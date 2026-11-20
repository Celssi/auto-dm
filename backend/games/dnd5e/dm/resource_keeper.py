"""Auto-update spell slots, concentration, Wild Shape, and short rest after each play turn."""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.games.dnd5e.characters.character_builder import apply_short_rest, long_rest_recover
from backend.games.dnd5e.characters.entity import (
    Dnd5eCharacter,
    character_from_dict,
    format_for_prompt,
)
from backend.games.dnd5e.characters.spell_resources import (
    apply_resource_updates,
    compute_wild_shape_max,
)
from backend.llm import structured_llm

_SHORT_REST_TRIGGERS = (
    "short rest",
    "short-rest",
    "brief rest",
    "take an hour to rest",
    "hour of rest",
    "hour to rest",
    "lyhyt lepo",
    "tunnin lepo",
)

_REST_REFUSAL = re.compile(
    r"(not possible|not applied|cannot rest|can't rest|can not rest|"
    r"no time to rest|too dangerous|not (a )?safe (place|time|moment)|"
    r"keep moving|rest will have to wait|no chance to rest|"
    r"do not rest|don't rest|no short rest|no long rest|"
    r"enemy .{0,80}approach|interrupted|"
    r"lepo saisi|saisi odottaa|kesken taistelun|"
    r"ei (voi |voida )?levät|ei lepoa|liian vaarallista|"
    r"taistelu(n)? (kesken|käynnissä))",
    re.IGNORECASE,
)
_SHORT_REST_GRANT = re.compile(
    r"(you (take|finish|complete) .{0,40}(short )?rest|"
    r"you settle .{0,40}(rest|hour)|"
    r"after (a |the )?short rest|"
    r"an hour (passes|later)|hour passes|feel refreshed|"
    r"lepä(ät|ätte|si)|tunnin lepo|tunti kuluu|virkisty)",
    re.IGNORECASE,
)
_LONG_REST_GRANT = re.compile(
    r"(you (take|finish|complete) .{0,40}long rest|after (a |the )?long rest|"
    r"eight hours|8 hours|you sleep|trance)",
    re.IGNORECASE,
)


class SpellCast(BaseModel):
    spell_name: str
    slot_level: int = Field(default=0, description="0 = default spell level; higher = upcast")
    ritual: bool = Field(default=False, description="Ritual cast, no slot spent")
    free_use: bool | None = Field(
        default=None, description="True if Magic Initiate free cast was used"
    )


class ResourceTurnUpdates(BaseModel):
    casts: list[SpellCast] = Field(default_factory=list)
    end_concentration: bool = Field(default=False)
    new_concentration: str = Field(
        default="", description="Spell name if concentrating, else empty"
    )
    wild_shape_used: bool = Field(default=False)
    short_rest: bool = Field(
        default=False, description="Character clearly finished a short rest this turn"
    )
    spend_hit_dice: int = Field(
        default=0, ge=0, le=20, description="Hit Dice spent during short rest, if stated"
    )


def rest_refused(dm_response: str) -> bool:
    return bool(_REST_REFUSAL.search(dm_response or ""))


def rest_granted(dm_response: str, *, kind: str = "short") -> bool:
    if rest_refused(dm_response):
        return False
    text = dm_response or ""
    if kind == "long":
        return bool(_LONG_REST_GRANT.search(text))
    return bool(_SHORT_REST_GRANT.search(text))


def combat_blocks_rest(*, in_combat: bool = False, combat_state: dict | None = None) -> bool:
    """True when a structured encounter is still active. Keyword in_combat is not enough."""
    raw = combat_state or {}
    status = str(raw.get("status") or "").strip().lower()
    if status == "active":
        return True
    if in_combat and status in {"active", "started"}:
        return True
    return False


def narrative_short_rest_detected(user_message: str, dm_response: str) -> bool:
    """True only when the DM actually grants a short rest, not merely when the player asks."""
    dm = (dm_response or "").lower()
    user = (user_message or "").lower()
    if "long rest" in dm or "long-rest" in dm:
        return False
    if rest_refused(dm_response):
        return False
    if rest_granted(dm_response, kind="short"):
        return True
    if any(trigger in user for trigger in _SHORT_REST_TRIGGERS) and rest_granted(
        dm_response, kind="short"
    ):
        return True
    return False


_AC_FROM_NARRATION = re.compile(
    r"\b(?:ac|armor class)\s*(?:is|now|:)?\s*(\d+)\b",
    re.IGNORECASE,
)
_HD_REMAINING = re.compile(
    r"\b(?:hit dice|hd)\s*(?:remaining|left|:)?\s*(\d+)\b|\b(\d+)\s*(?:hit dice|hd)\b",
    re.IGNORECASE,
)
_MAGE_ARMOR_ACTIVE = re.compile(
    r"mage armour|mage armor",
    re.IGNORECASE,
)
_SHEET_RECONCILE = re.compile(
    r"hp\s+(\d+)\s*/\s*(\d+)[,;.\s]+ac\s+(\d+)[,;.\s]+(?:hd|hit dice)\s+(\d+)",
    re.IGNORECASE,
)


def parse_pc_hp_from_narration(
    dm_response: str,
    *,
    name: str,
    max_hp: int,
    current_hp: int,
) -> int | None:
    """Read the player character's HP from DM prose when clearly stated."""
    text = dm_response or ""
    if not text.strip() or max_hp <= 0:
        return None
    name_pat = re.escape((name or "").strip()) if (name or "").strip() else ""
    patterns: list[re.Pattern[str]] = [
        re.compile(r"\byour (?:hp|hit points?)\s*(?:are|is|now|:)?\s*(\d+)\s*/\s*(\d+)", re.I),
        re.compile(r"\byou (?:are|drop|are reduced) (?:to|down to)\s*(\d+)\s*(?:hp|hit points?)\b", re.I),
        re.compile(r"\b(?:hp|hit points?|osumapiste(?:et|itä)?|op)\s*(?:are|is|now|on|nyt|:)?\s*(\d+)\s*/\s*(\d+)", re.I),
        re.compile(r"\b(\d+)\s*/\s*(\d+)\s*(?:hp|hit points?|osumapist)\b", re.I),
        re.compile(r"\bleave things at\s+(\d+)\s*(?:hp|hit points?)\b", re.I),
        re.compile(r"\bat\s+(\d+)\s*(?:hp|hit points?)\b", re.I),
        re.compile(r"HP\s*[:=]?\s*(\d+)\s*/\s*(\d+)", re.I),
    ]
    if name_pat:
        patterns.insert(
            0,
            re.compile(
                rf"{name_pat}.{{0,48}}(?:hp|hit points?)\s*(?:are|is|now|:)?\s*(\d+)\s*(?:/\s*(\d+))?",
                re.I,
            ),
        )
    found: int | None = None
    for pattern in patterns:
        for match in pattern.finditer(text):
            hp = int(match.group(1))
            mx = int(match.group(2)) if match.lastindex and match.lastindex >= 2 and match.group(2) else max_hp
            if mx == max_hp and 0 <= hp <= max_hp:
                found = hp
                if hp != current_hp:
                    return hp
    return found


def parse_ac_from_narration(dm_response: str) -> int | None:
    text = dm_response or ""
    for match in _AC_FROM_NARRATION.finditer(text):
        ac = int(match.group(1))
        if 1 <= ac <= 40:
            return ac
    return None


def parse_hit_dice_remaining(dm_response: str, *, hit_dice_max: int) -> int | None:
    if hit_dice_max <= 0:
        return None
    text = dm_response or ""
    for match in _HD_REMAINING.finditer(text):
        remaining = int(match.group(1) or match.group(2) or 0)
        if 0 <= remaining <= hit_dice_max:
            return remaining
    return None


_MAGE_ARMOR_CAST = re.compile(
    r"(?:cast|casting|casts|loitsit|loiti|aktivoi(?:t)?|weave[sd]?).{0,48}mage armou?r|"
    r"mage armou?r.{0,48}(?:takes effect|is active|holds|surround|shimmer|on voimassa|aktiivinen)",
    re.IGNORECASE,
)


def narration_sets_mage_armor(dm_response: str) -> bool:
    text = dm_response or ""
    if not _MAGE_ARMOR_ACTIVE.search(text):
        return False
    lower = text.lower()
    if any(token in lower for token in ("ended", "expires", "expired", "drops", "no longer")):
        return False
    return bool(_MAGE_ARMOR_CAST.search(text))


def overlay_live_resources(character: dict, dm_response: str) -> dict:
    """Apply HP/AC/HD/Mage Armor stated in DM prose onto the character dict."""
    from backend.games.dnd5e.characters.class_resources import compute_ac_details
    from backend.games.dnd5e.characters.spell_resources import set_mage_armor_active

    char = character_from_dict(character)
    updates: dict = {}
    logs: list[str] = []
    text = dm_response or ""
    reconcile_matches = list(_SHEET_RECONCILE.finditer(text))
    reconcile = reconcile_matches[-1] if reconcile_matches else None
    hp = parse_pc_hp_from_narration(
        dm_response, name=char.name, max_hp=char.max_hp, current_hp=char.hp
    )
    if reconcile:
        hp = int(reconcile.group(1))
    if hp is not None and hp != char.hp:
        char.hp = hp
        updates["hp"] = hp
        logs.append(f"HP set to {hp}/{char.max_hp} from DM narration.")
    remaining = parse_hit_dice_remaining(dm_response, hit_dice_max=char.hit_dice_max)
    if reconcile:
        remaining = int(reconcile.group(4))
    if remaining is not None:
        spent = max(0, char.hit_dice_max - remaining)
        if spent != char.hit_dice_spent:
            char.hit_dice_spent = spent
            updates["hit_dice_spent"] = spent
            logs.append(f"Hit Dice remaining {remaining}/{char.hit_dice_max}.")
    ac_from_text = parse_ac_from_narration(dm_response)
    if reconcile:
        ac_from_text = int(reconcile.group(3))
    if narration_sets_mage_armor(dm_response):
        set_mage_armor_active(char, True)
        updates["feature_choices"] = dict(char.feature_choices or {})
    if not char.ac_manual:
        computed = int(compute_ac_details(char)["computed"])
        if computed != char.ac:
            char.ac = computed
            updates["ac"] = computed
            logs.append(f"AC set to {computed}.")
    elif ac_from_text is not None and ac_from_text != char.ac:
        char.ac = ac_from_text
        updates["ac"] = ac_from_text
    if updates.get("feature_choices") is None and "ac" in updates:
        updates["feature_choices"] = dict(char.feature_choices or {})
    updates["_logs"] = logs
    return updates


_NO_HIT_DICE = re.compile(
    r"(no hit dice|without (spending |using )?hit dice|do not spend .{0,24}hit dice|"
    r"don't spend .{0,24}hit dice|already at full|full hit points|"
    r"no need (to spend|for) hit dice|hit dice .{0,20}not needed)",
    re.IGNORECASE,
)


def no_hit_dice_requested(user_message: str, dm_response: str) -> bool:
    return bool(_NO_HIT_DICE.search(f"{user_message}\n{dm_response}"))


def parse_hit_dice_to_spend(user_message: str, dm_response: str) -> int:
    text = f"{user_message}\n{dm_response}"
    if no_hit_dice_requested(user_message, dm_response):
        return 0
    for pattern in (
        r"spend\s+(\d+)\s+hit\s+dice",
        r"spend\s+(\d+)\s+hit\s+die",
        r"uses?\s+(\d+)\s+hit\s+dice",
        r"(\d+)\s+hit\s+dice\s+spent",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return max(0, int(match.group(1)))
    return 0


def _apply_short_rest_updates(
    char: Dnd5eCharacter, *, dice_to_spend: int
) -> tuple[dict, list[str]]:
    rest = apply_short_rest(char, dice_to_spend=dice_to_spend)
    entity = dict(rest.get("entity_updates") or {})
    summary = str(rest.get("summary") or "Short rest.")
    if not entity:
        return {}, [summary]
    return entity, [summary]


def extract_resource_updates(
    *,
    char: Dnd5eCharacter,
    user_message: str,
    dm_response: str,
) -> ResourceTurnUpdates:
    ws_max = compute_wild_shape_max(char)
    prompt = f"""Analyze this D&D 5e solo play turn for RESOURCE changes only.

Character resources:
{format_for_prompt(char)[:3500]}

Rules:
- short_rest: true ONLY if the player or DM clearly completes a short rest (about 1 hour) this turn
  - spend_hit_dice: number of Hit Dice clearly spent for healing during that rest (0 if none stated)
  - If short_rest is true, leave casts empty and other fields false/default
- casts: ONLY when the player or DM clearly casts a leveled spell
  or cantrip this turn (not during a rest)
  - ritual=true only if explicitly a ritual cast (10+ min, no slot)
  - slot_level: set only for upcasting
    (e.g. Healing Word at 2nd level -> slot_level=2)
  - Cantrips: include in casts but they never spend slots
- new_concentration: spell name if a concentration spell begins; empty otherwise
- end_concentration: true only if concentration clearly ended
  (new conc spell, dropped, incapacitated)
- wild_shape_used: true only if Wild Shape was activated this turn\
{f" (max {ws_max} uses/long rest)" if ws_max else ""}
- Do NOT guess. Prefer empty lists/false over speculation.
- Long rest is handled elsewhere — do not set short_rest for a long rest.

Player: {user_message[:1500]}

DM response: {dm_response[:1500]}
"""
    llm = structured_llm(ResourceTurnUpdates)
    return llm.invoke([HumanMessage(content=prompt)])


def run_resource_keeper(
    *,
    character: dict,
    user_message: str,
    dm_response: str,
    combat_active: bool = False,
) -> tuple[dict, list[str]]:
    if not dm_response.strip():
        return {}, []
    char = character_from_dict(character)

    if rest_refused(dm_response):
        entity: dict = {}
        logs: list[str] = ["Rest not applied: the DM did not grant a rest."]
        hp = parse_pc_hp_from_narration(
            dm_response, name=char.name, max_hp=char.max_hp, current_hp=char.hp
        )
        if hp is not None and hp != char.hp:
            char.hp = hp
            entity["hp"] = hp
            logs.append(f"HP set to {hp}/{char.max_hp} from DM narration.")
        return entity, logs

    from backend.games.dnd5e.dm.spell_autocomplete import extract_cast_query, resolve_spell_query
    from backend.games.dnd5e.characters.spell_resources import apply_spell_cast

    query = extract_cast_query(user_message)
    if query and not cast_refused(dm_response):
        resolution = resolve_spell_query(char, query)
        if resolution.status == "exact" and resolution.spell_name:
            ok, msg = apply_spell_cast(
                char,
                resolution.spell_name,
                requested_text=user_message,
                inferred=False,
                audit_source="resource_keeper",
            )
            entity, logs = apply_resource_updates(char, ResourceTurnUpdates())
            if msg:
                logs = [msg if ok else f"⚠ {msg}"] + logs
            hp = parse_pc_hp_from_narration(
                dm_response, name=char.name, max_hp=char.max_hp, current_hp=char.hp
            )
            if hp is not None:
                char.hp = hp
                entity["hp"] = hp
                logs.append(f"HP set to {hp}/{char.max_hp} from DM narration.")
            return entity, logs

    if not combat_active and narrative_short_rest_detected(user_message, dm_response):
        dice = parse_hit_dice_to_spend(user_message, dm_response)
        return _apply_short_rest_updates(char, dice_to_spend=dice)

    combined = f"{user_message}\n{dm_response}".lower()
    needs_llm = any(
        token in combined
        for token in ("cast ", "/cast", "wild shape", "short rest", "long rest", "lyhyt lepo", "pitkä lepo")
    )
    if not needs_llm:
        hp = parse_pc_hp_from_narration(
            dm_response, name=char.name, max_hp=char.max_hp, current_hp=char.hp
        )
        if hp is not None and hp != char.hp:
            return {"hp": hp}, [f"HP set to {hp}/{char.max_hp} from DM narration."]
        return {}, []

    updates = extract_resource_updates(
        char=char, user_message=user_message, dm_response=dm_response
    )
    if updates.short_rest and not combat_active and rest_granted(dm_response, kind="short"):
        return _apply_short_rest_updates(char, dice_to_spend=updates.spend_hit_dice)

    entity_updates, logs = apply_resource_updates(char, updates)
    hp = parse_pc_hp_from_narration(
        dm_response, name=char.name, max_hp=char.max_hp, current_hp=char.hp
    )
    if hp is not None and hp != char.hp:
        char.hp = hp
        entity_updates["hp"] = hp
        logs.append(f"HP set to {hp}/{char.max_hp} from DM narration.")
    if not entity_updates and not logs:
        return {}, []
    return entity_updates, logs


def apply_pending_rest(
    character: dict,
    pending: dict,
    dm_response: str,
    *,
    combat_active: bool = False,
    user_message: str = "",
) -> tuple[dict, list[str]]:
    """Apply a shortcut rest only after the DM grants it, and never during combat."""
    kind = str(pending.get("kind") or "short").strip().lower()
    if combat_active:
        return {}, ["Rest not applied: combat is still underway."]
    if rest_refused(dm_response) or not rest_granted(dm_response, kind=kind):
        reason = "the DM did not grant a rest"
        if rest_refused(dm_response):
            reason = "the DM refused the rest"
        return {}, [f"Rest not applied: {reason}."]
    live = overlay_live_resources(character, dm_response)
    live.pop("_logs", None)
    merged = {**character, **live}
    char = character_from_dict(merged)
    hp = parse_pc_hp_from_narration(
        dm_response, name=char.name, max_hp=char.max_hp, current_hp=char.hp
    )
    if hp is not None:
        char.hp = hp
    if kind == "long":
        rest = long_rest_recover(char)
        return dict(rest.get("entity_updates") or {}), [str(rest.get("summary") or "Long rest.")]
    dice = int(pending.get("dice_to_spend") or 0)
    parsed = parse_hit_dice_to_spend(user_message, dm_response)
    if parsed:
        dice = parsed
    if no_hit_dice_requested(user_message, dm_response) or char.hp >= char.max_hp:
        dice = 0
    return _apply_short_rest_updates(char, dice_to_spend=dice)


_CAST_REFUSAL = re.compile(
    r"(already active|already in effect|still holds|still in effect|"
    r"no need to (re)?cast|do not (re)?cast|don't (re)?cast|"
    r"cannot cast|can't cast|ward still|remains in effect|"
    r"no slot (is )?spent|without spending a slot|"
    r"ei tarvitse loitsia|jo voimassa)",
    re.IGNORECASE,
)


def cast_refused(dm_response: str) -> bool:
    return bool(_CAST_REFUSAL.search(dm_response or ""))


def apply_pending_cast(
    character: dict,
    pending: dict,
    dm_response: str,
) -> tuple[dict, list[str]]:
    """Spend a shortcut cast only if the DM did not refuse it."""
    if cast_refused(dm_response):
        return {}, ["Cast not applied: the DM refused the spell."]
    spell_name = str(pending.get("spell_name") or "").strip()
    if not spell_name:
        return {}, ["Cast not applied: no spell named."]
    return apply_cast_spell_shortcut(
        character,
        spell_name,
        slot_level=int(pending.get("slot_level") or 0),
        ritual=bool(pending.get("ritual")),
        free_use=pending.get("free_use"),
        requested_text=str(pending.get("requested_text") or ""),
        audit_source="pending_cast",
    )


def apply_cast_spell_shortcut(
    character: dict,
    spell_name: str,
    *,
    slot_level: int = 0,
    ritual: bool = False,
    audit_source: str = "shortcut",
    free_use: bool | None = None,
    requested_text: str = "",
) -> tuple[dict, list[str]]:
    """Deterministic spell cast without LLM (shortcut)."""
    char = character_from_dict(character)
    from backend.games.dnd5e.characters.class_resources import compute_ac_details
    from backend.games.dnd5e.characters.spell_resources import apply_spell_cast

    ok, msg = apply_spell_cast(
        char,
        spell_name,
        slot_level=slot_level,
        ritual=ritual,
        audit_source=audit_source,
        inferred=False,
        free_use=free_use,
        requested_text=requested_text,
    )
    if not char.ac_manual:
        char.ac = int(compute_ac_details(char)["computed"])
    entity = {
        "spell_slots": dict(char.spell_slots),
        "concentration": char.concentration,
        "wild_shape_uses": char.wild_shape_uses,
        "feature_choices": dict(char.feature_choices or {}),
        "ac": char.ac,
        "hp": char.hp,
    }
    return entity, [msg if ok else f"⚠ {msg}"]
