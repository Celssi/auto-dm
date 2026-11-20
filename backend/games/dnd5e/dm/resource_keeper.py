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
    r"(cannot rest|can't rest|can not rest|no time to rest|"
    r"too dangerous to rest|not (a )?safe (place|time|moment) to rest|"
    r"rest will have to wait|no chance to rest|"
    r"(do not|don't) (take a |take the )?(short |long )?rest|"
    r"no short rest|no long rest|"
    r"(short |long )?rest[:\s]+not possible|"
    r"(short |long )?rest (is |was )?(not possible|impossible|refused)|"
    r"lepo saisi|saisi odottaa|kesken taistelun|"
    r"ei (voi |voida )?levät|ei lepoa|liian vaarallista|"
    r"taistelu(n)? (kesken|käynnissä))",
    re.IGNORECASE,
)
_SHORT_REST_GRANT = re.compile(
    r"(you (take|finish|complete|spend) .{0,40}(short )?rest|"
    r"you settle .{0,40}(rest|hour)|"
    r"after (a |the )?short rest|"
    r"(a |the )?short rest (is |was )?(complete|done|over|finished)|"
    r"an hour (passes|later)|after an hour|hour passes|feel refreshed|"
    r"you rest\b|rest for (an |one )?hour|for an hour|"
    r"sit for .{0,20}hour|catch your breath|take a breather|"
    r"an hour of rest|hour of rest|"
    r"hit (?:die|dice) (spent|used|rolled)|"
    r"spent .{0,24}hit (?:die|dice)|"
    r"arcane recovery|"
    r"prone ended|no longer prone|"
    r"lepä(ät|ätte|si)|tunnin lepo|tunti kuluu|virkisty)",
    re.IGNORECASE,
)
_REST_EFFECTS = re.compile(
    r"(hit (?:die|dice) (spent|used|rolled)|spent .{0,24}hit (?:die|dice)|"
    r"arcane recovery|"
    r"pact magic.{0,32}(return|recover)|"
    r"wounds (close|ease))",
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
    return bool(_SHORT_REST_GRANT.search(text) or _REST_EFFECTS.search(text))


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
    """True only when the player asked to rest and the DM granted it."""
    dm = (dm_response or "").lower()
    user = (user_message or "").lower()
    if "long rest" in dm or "long-rest" in dm:
        return False
    if rest_refused(dm_response):
        return False
    user_asked = any(trigger in user for trigger in _SHORT_REST_TRIGGERS)
    if not user_asked:
        return False
    return rest_granted(dm_response, kind="short")


_AC_FROM_NARRATION = re.compile(
    r"\b(?:ac|armor class)\s*(?:is|now|:)?\s*(\d+)\b",
    re.IGNORECASE,
)
_HD_REMAINING = re.compile(
    r"(?:hit dice|hd)\s+(?:remaining|left)\s*[:=]?\s*(\d+)\b|"
    r"(\d+)\s+(?:hit dice|hd)\s+(?:remaining|left)\b",
    re.IGNORECASE,
)
_HD_UNUSED = re.compile(
    r"(hit dice|hd).{0,24}(unused|not spent|not used)|"
    r"(unused|not spent|not used).{0,24}(hit dice|hd)|"
    r"no need (to spend|for) hit dice",
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


def _hp_value_fits(hp: int, mx: int, max_hp: int) -> bool:
    if hp < 0 or max_hp <= 0:
        return False
    if hp > max_hp:
        return False
    return mx in (0, max_hp) or abs(mx - max_hp) <= 2


_THIS_TURN_DAMAGE = re.compile(
    r"(?:falling|fall damage|bludgeoning)[^.\n]{0,80}?(?:1d6|d6)\s*=\s*(\d+)"
    r"|(?:1d6|d6)\s*=\s*(\d+)[^.\n]{0,48}(?:fall|falling|bludgeoning)"
    r"|(?:take|takes|taken|deal|deals|suffer|suffers)\s+(\d+)\s+(?:points? of )?damage",
    re.IGNORECASE,
)
_HP_ARROW = re.compile(
    r"\bhp\s+(\d+)\s*(?:/\s*\d+)?\s*(?:->|to)\s*(\d+)\s*/\s*(\d+)",
    re.IGNORECASE,
)
_FRAC_ARROW = re.compile(
    r"\b(\d+)\s*/\s*(\d+)\s*(?:->|to)\s*(\d+)\s*/\s*(\d+)",
    re.IGNORECASE,
)


def parse_this_turn_damage(dm_response: str) -> int | None:
    """Last fall/damage roll in this reply. Ignores earlier recap dice."""
    found: int | None = None
    for match in _THIS_TURN_DAMAGE.finditer(dm_response or ""):
        for group in match.groups():
            if group:
                found = int(group)
    return found


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
    hits: list[tuple[int, int]] = []

    def add(start: int, hp: int, mx: int) -> None:
        if _hp_value_fits(hp, mx, max_hp):
            hits.append((start, hp))

    for match in _HP_ARROW.finditer(text):
        add(match.start(), int(match.group(2)), int(match.group(3)))
    for match in _FRAC_ARROW.finditer(text):
        add(match.start(), int(match.group(3)), int(match.group(4)))
    name_pat = re.escape((name or "").strip()) if (name or "").strip() else ""
    patterns: list[re.Pattern[str]] = [
        re.compile(r"\byour (?:hp|hit points?)\s*(?:are|is|now|:)?\s*(\d+)\s*/\s*(\d+)", re.I),
        re.compile(r"\byou (?:are|drop|are reduced) (?:to|down to)\s*(\d+)\s*(?:hp|hit points?)\b", re.I),
        re.compile(r"\b(?:hp|hit points?|osumapiste(?:et|itä)?|op)\s*(?:are|is|now|on|nyt|:)?\s*(\d+)\s*/\s*(\d+)", re.I),
        re.compile(r"\b(\d+)\s*/\s*(\d+)\s*(?:hp|hit points?|osumapist)\b", re.I),
        re.compile(r"\bleave things at\s+(\d+)\s*(?:hp|hit points?)\b", re.I),
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
    for pattern in patterns:
        for match in pattern.finditer(text):
            hp = int(match.group(1))
            mx = int(match.group(2)) if match.lastindex and match.lastindex >= 2 and match.group(2) else max_hp
            add(match.start(), hp, mx)
    hits.sort()
    candidates = [hp for _, hp in hits]
    differing = [hp for hp in candidates if hp != current_hp]
    found = differing[-1] if differing else (candidates[-1] if candidates else None)
    damage = parse_this_turn_damage(text)
    if damage is not None:
        from_dice = max(0, min(max_hp, current_hp - damage))
        if found is None:
            return from_dice
        implied = current_hp - found
        if implied > damage + 1:
            return from_dice
        return found
    return found


def parse_ac_from_narration(dm_response: str) -> int | None:
    text = dm_response or ""
    for match in _AC_FROM_NARRATION.finditer(text):
        ac = int(match.group(1))
        if 1 <= ac <= 40:
            return ac
    return None


_CONCENTRATION_END = re.compile(
    r"\b(concentration (ends|broken|dropped|lost)|stop concentrating|you drop concentration)\b",
    re.IGNORECASE,
)
_CONCENTRATION_SPELL = re.compile(
    r"\bconcentrat(?:e|ing|ion)\b.{0,48}\b(bless|shield of faith|hunter's mark|hex|faerie fire|"
    r"hold person|spirit guardians|moonbeam|web|heat metal|compelled duel)\b",
    re.IGNORECASE,
)
_LOH_SPEND = re.compile(
    r"(?:lay on hands|loh).{0,40}?(?:heal|restore|spend|use|using).{0,20}?(\d+)|"
    r"(?:heal|restore|spend|use).{0,20}?(\d+).{0,24}(?:lay on hands|loh)|"
    r"(?:lay on hands|loh)\s+(\d+)\s*(?:points?|hp)?",
    re.IGNORECASE,
)
_SAVE_DC = re.compile(r"\bdc\s*(\d+)\b", re.IGNORECASE)
_SCENE_MOVE = re.compile(
    r"\byou (?:step|move|walk|enter|leave|advance|retreat|climb|cross|push (?:in|inside|through))"
    r".{0,80}",
    re.IGNORECASE,
)


def parse_concentration_from_narration(dm_response: str, current: str = "") -> str | None:
    text = dm_response or ""
    if not text.strip():
        return None
    if _CONCENTRATION_END.search(text):
        return ""
    found = None
    for match in _CONCENTRATION_SPELL.finditer(text):
        found = match.group(1).strip().title()
    return found


def parse_lay_on_hands_spend(dm_response: str, remaining: int) -> int | None:
    if remaining < 0:
        return None
    found = None
    for match in _LOH_SPEND.finditer(dm_response or ""):
        for group in match.groups():
            if group:
                found = int(group)
    if found is None:
        return None
    return max(0, remaining - found)


def merge_active_effects(
    current: list,
    conditions: list[str],
    dm_response: str,
) -> list[dict]:
    """Keep a fixed save DC per ongoing condition; do not invent a new DC."""
    conds = [str(c).strip() for c in conditions if str(c).strip()]
    cond_keys = {c.lower() for c in conds}
    by_name: dict[str, dict] = {}
    for item in current or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            by_name[name.lower()] = dict(item)
    dcs = [int(m.group(1)) for m in _SAVE_DC.finditer(dm_response or "")]
    latest_dc = dcs[-1] if dcs else None
    out: list[dict] = []
    for cond in conds:
        key = cond.lower()
        prev = by_name.get(key) or {}
        dc = prev.get("save_dc")
        if not isinstance(dc, int) and latest_dc is not None and key in (dm_response or "").lower():
            dc = latest_dc
        out.append(
            {
                "name": str(prev.get("name") or cond),
                "source": str(prev.get("source") or "").strip(),
                "save_dc": dc if isinstance(dc, int) else None,
            }
        )
    return out


def parse_scene_position(dm_response: str, current: str = "") -> str:
    text = (dm_response or "").strip()
    if not text:
        return current
    match = None
    for found in _SCENE_MOVE.finditer(text):
        match = found
    if not match:
        return current
    clause = re.sub(r"\s+", " ", match.group(0)).strip(" .")
    return clause[:120] or current


def parse_hit_dice_remaining(dm_response: str, *, hit_dice_max: int) -> int | None:
    if hit_dice_max <= 0:
        return None
    text = dm_response or ""
    if _HD_UNUSED.search(text):
        return hit_dice_max
    found: int | None = None
    for match in _HD_REMAINING.finditer(text):
        remaining = int(match.group(1) or match.group(2) or 0)
        if 0 <= remaining <= hit_dice_max:
            found = remaining
    return found


_MAGE_ARMOR_CAST = re.compile(
    r"(?:cast|casting|casts|loitsit|loiti|aktivoi(?:t)?|weave[sd]?).{0,48}mage armou?r|"
    r"mage armou?r.{0,48}(?:takes effect|is active|holds|surround|shimmer|on voimassa|aktiivinen)",
    re.IGNORECASE,
)


_SHEET_CONDITIONS = (
    "Blinded",
    "Charmed",
    "Deafened",
    "Frightened",
    "Grappled",
    "Incapacitated",
    "Invisible",
    "Paralyzed",
    "Petrified",
    "Poisoned",
    "Prone",
    "Restrained",
    "Stunned",
    "Unconscious",
)


def _pc_gains_condition(lower: str, token: str) -> bool:
    if token == "prone" and re.search(
        r"\b(fall|falls|falling|knocked|land|lands)\b.{0,80}\bprone\b|"
        r"\bprone\b.{0,24}\b(you|your)\b|"
        r"\byou\b.{0,40}\bprone\b",
        lower,
    ):
        return True
    return bool(
        re.search(
            rf"\b(you|you're|you are|your)\b.{{0,48}}\b{token}\b|"
            rf"\bbecome[s]?\s+{token}\b|"
            rf"\bgain[s]?\s+(?:the\s+)?{token}\b|"
            rf"\bnow\s+{token}\b",
            lower,
        )
    )


def parse_conditions_from_narration(
    dm_response: str, current: list | None = None
) -> list[str]:
    """Merge D&D 2024 conditions that actually apply to the player this turn."""
    lower = (dm_response or "").lower()
    out: list[str] = []
    seen: set[str] = set()
    for raw in current or []:
        key = str(raw).strip()
        if not key:
            continue
        token = key.lower()
        if token not in seen:
            seen.add(token)
            out.append(key)
    if not lower.strip():
        return out
    stood_up = bool(re.search(r"\bstands? up\b|\bstand up\b|\bgetting up\b|\bprone ended\b", lower))
    for cond in _SHEET_CONDITIONS:
        token = cond.lower()
        cleared = bool(
            re.search(
                rf"\b(you|you're|you are|your)\b.{{0,40}}(?:no longer|not|aren't|are not)\s+{token}\b|"
                rf"\b(?:the )?{token}(?: condition)?\s+ended\b|"
                rf"\bno longer\s+{token}\b",
                lower,
            )
        )
        if cond == "Prone" and stood_up:
            cleared = True
        if cleared:
            out = [item for item in out if item.lower() != token]
            seen.discard(token)
            continue
        if token not in seen and _pc_gains_condition(lower, token):
            seen.add(token)
            out.append(cond)
    return out


def narration_sets_mage_armor(dm_response: str) -> bool:
    text = dm_response or ""
    if not _MAGE_ARMOR_ACTIVE.search(text):
        return False
    lower = text.lower()
    if any(token in lower for token in ("ended", "expires", "expired", "drops", "no longer")):
        return False
    return bool(_MAGE_ARMOR_CAST.search(text))


def overlay_live_resources(character: dict, dm_response: str) -> dict:
    """Apply HP/AC/HD/conditions/Mage Armor stated in DM prose onto the character dict."""
    from backend.games.dnd5e.characters.class_resources import compute_ac_details
    from backend.games.dnd5e.characters.spell_resources import set_mage_armor_active

    char = character_from_dict(character)
    stored_max = int(character.get("max_hp") or 0)
    stored_hp = character.get("hp")
    max_hp = stored_max or int(char.max_hp or 0)
    current_hp = int(stored_hp) if stored_hp is not None else int(char.hp or 0)
    updates: dict = {}
    logs: list[str] = []
    text = dm_response or ""
    reconcile_matches = list(_SHEET_RECONCILE.finditer(text))
    reconcile = reconcile_matches[-1] if reconcile_matches else None
    hp = parse_pc_hp_from_narration(
        dm_response, name=char.name, max_hp=max_hp, current_hp=current_hp
    )
    if reconcile:
        hp = int(reconcile.group(1))
    if hp is not None and hp != current_hp:
        old_hp = current_hp
        char.hp = hp
        updates["hp"] = hp
        if hp < old_hp:
            logs.append(f"Took {old_hp - hp} damage (HP {old_hp} -> {hp}/{max_hp}).")
        else:
            logs.append(f"HP set to {hp}/{max_hp} from DM narration.")
    new_conditions = parse_conditions_from_narration(
        dm_response, list(character.get("conditions") or char.conditions or [])
    )
    old_conditions = [str(item).strip().lower() for item in (character.get("conditions") or char.conditions or [])]
    if [c.lower() for c in new_conditions] != old_conditions:
        updates["conditions"] = new_conditions
        added = [c for c in new_conditions if c.lower() not in old_conditions]
        if added:
            logs.append("Conditions: " + ", ".join(added) + ".")
    remaining = parse_hit_dice_remaining(dm_response, hit_dice_max=char.hit_dice_max)
    if reconcile and not _HD_UNUSED.search(text):
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
    conc = parse_concentration_from_narration(text, char.concentration)
    if conc is not None and conc != (char.concentration or ""):
        updates["concentration"] = conc
        logs.append(f"Concentration: {conc or 'none'}.")
    loh = parse_lay_on_hands_spend(text, char.lay_on_hands_remaining)
    if loh is not None and loh != char.lay_on_hands_remaining:
        updates["lay_on_hands_remaining"] = loh
        logs.append(f"Lay on Hands {char.lay_on_hands_remaining} -> {loh}.")
    effects = merge_active_effects(
        list(character.get("active_effects") or char.active_effects or []),
        list(updates.get("conditions") or character.get("conditions") or char.conditions or []),
        text,
    )
    if effects != list(character.get("active_effects") or char.active_effects or []):
        updates["active_effects"] = effects
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
        r"(\d+)\s+hit\s+(?:die|dice)\s+spent",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return max(0, int(match.group(1)))
    if re.search(r"hit\s+(?:die|dice)\s+spent", text, re.IGNORECASE):
        return 1
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
    granted = rest_granted(dm_response, kind=kind)
    if not granted and not rest_refused(dm_response):
        granted = bool(
            re.search(
                r"\b(short rest|long rest|you rest|an hour|catch your breath|take a breather)\b",
                dm_response or "",
                re.IGNORECASE,
            )
        )
    if rest_refused(dm_response) or not granted:
        reason = "the DM did not grant a rest"
        if rest_refused(dm_response):
            reason = "the DM refused the rest"
        return {}, [f"Rest not applied: {reason}."]
    char = character_from_dict(character)
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
