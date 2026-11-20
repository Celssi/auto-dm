"""Structured mechanics delta emitted by the narrator in the same LLM turn.

The player-facing narration is never parsed for HP, conditions, rest, or resources.
A fenced JSON block after the prose is the only source of mechanical change.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.games.dnd5e.characters.entity import (
    character_from_dict,
    character_to_dict,
)

MECHANICS_START = "<<<MECHANICS"
MECHANICS_END = ">>>"

SHEET_CONDITIONS = (
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
_CONDITION_BY_KEY = {name.lower(): name for name in SHEET_CONDITIONS}

RestKind = Literal["none", "short", "long", "interrupted"]
ConcentrationAction = Literal["none", "start", "end"]
InspirationAction = Literal["none", "grant", "spend"]
NpcAction = Literal["introduce", "update", "rename", "remove"]


class HpChange(BaseModel):
    amount: int = Field(description="Negative for damage, positive for healing")
    source: str = ""


class ConditionChange(BaseModel):
    name: str
    action: Literal["add", "remove"] = "add"
    save_dc: int | None = None
    source: str = ""


class ResourceUse(BaseModel):
    lay_on_hands: int = Field(default=0, description="Pool points spent this turn")
    hit_dice: int = 0
    heroic_inspiration: InspirationAction = "none"
    wild_shape: bool = False
    second_wind: bool = False


class ConcentrationChange(BaseModel):
    action: ConcentrationAction = "none"
    spell: str = ""


class RestChange(BaseModel):
    kind: RestKind = "none"
    hit_dice_spent: int | None = None


class CoinChange(BaseModel):
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0


class ItemChange(BaseModel):
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class NpcEntry(BaseModel):
    name: str
    action: NpcAction = "introduce"
    renamed_from: str = ""
    status: str = ""
    note: str = ""


class ReactionPrompt(BaseModel):
    kind: str = Field(description="opportunity_attack, shield, or similar")
    prompt: str = ""
    target: str = ""


class SpellCastDelta(BaseModel):
    spell_name: str = ""
    slot_level: int = 0
    ritual: bool = False
    free_use: bool = False
    refused: bool = False


class MechanicsDelta(BaseModel):
    hp_changes: list[HpChange] = Field(default_factory=list)
    conditions: list[ConditionChange] = Field(default_factory=list)
    resources: ResourceUse = Field(default_factory=ResourceUse)
    concentration: ConcentrationChange = Field(default_factory=ConcentrationChange)
    rest: RestChange = Field(default_factory=RestChange)
    coins: CoinChange = Field(default_factory=CoinChange)
    items: ItemChange = Field(default_factory=ItemChange)
    npcs: list[NpcEntry] = Field(default_factory=list)
    scene_position: str = ""
    reaction_prompt: ReactionPrompt | None = None
    spell_casts: list[SpellCastDelta] = Field(default_factory=list)
    refused: list[str] = Field(
        default_factory=list,
        description="Player actions the DM blocked this turn, e.g. rest or cast",
    )

    @field_validator("refused", mode="before")
    @classmethod
    def _clean_refused(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value.strip().lower()] if value.strip() else []
        return [str(item).strip().lower() for item in value if str(item).strip()]


EMPTY_DELTA = MechanicsDelta()

MECHANICS_INSTRUCTIONS = f"""After the player-facing narration, output a mechanics block. The block is stripped
before the player sees the reply. Never put mechanics JSON in the visible prose.

Rules for the block:
- hp_changes: only damage or healing that is NOT already on the live Character sheet.
  amount is negative for damage (trap, ghost, weapon) and positive for healing.
  Include source (trap, ghost, longsword, Lay on Hands).
- conditions: only conditions that apply to the player character. add only if the
  condition actually takes effect (a succeeded save does not add it). remove when it ends.
  save_dc is required when adding a condition that has a save, and stays fixed.
- resources: lay_on_hands is points spent this turn (0 if none). Never recap an older spend.
- concentration: start with the spell name, or end when it drops. none if unchanged.
- rest: long, short, interrupted, or none. Interrupted long rest uses short-rest benefits only.
  Do not mark long if the rest was interrupted. Do not roll Hit Dice in the visible prose;
  set rest.hit_dice_spent to the number of dice spent (usually 1). The server rolls once.
- spell_casts: required whenever a leveled spell is cast, including Bless. Starting
  concentration on a leveled spell must include a matching spell_casts entry so the slot
  is spent. Cantrips and refused casts do not spend slots.
- npcs: named people or creatures introduced, renamed, or updated. Never list rules terms,
  feats, spells, conditions, or action phrases (Bless, Savage Attacker, Disadvantage, Grab X).
- reaction_prompt: if the player could spend a reaction (opportunity attack, Shield, Uncanny
  Dodge), ASK. Do not resolve it. Set kind and a one-line prompt.
- Never spend the player's reaction, opportunity attack, or Shield without the player choosing.
- Fill only what changed. Use empty lists and none when nothing happened.

{MECHANICS_START}
{{"hp_changes":[],"conditions":[],"resources":{{}},"concentration":{{"action":"none"}},"rest":{{"kind":"none"}},"coins":{{}},"items":{{}},"npcs":[],"scene_position":"","reaction_prompt":null,"spell_casts":[],"refused":[]}}
{MECHANICS_END}
"""


def empty_delta() -> MechanicsDelta:
    return MechanicsDelta()


def render_mechanics_block(delta: MechanicsDelta | dict | None) -> str:
    parsed = delta if isinstance(delta, MechanicsDelta) else MechanicsDelta.model_validate(delta or {})
    return f"{MECHANICS_START}\n{parsed.model_dump_json()}\n{MECHANICS_END}"


def _extract_json_object(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return ""
    return text[start : end + 1]


def parse_mechanics_delta(raw: str | None) -> MechanicsDelta:
    blob = _extract_json_object(raw or "")
    if not blob:
        return empty_delta()
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return empty_delta()
    if not isinstance(data, dict):
        return empty_delta()
    try:
        return MechanicsDelta.model_validate(data)
    except Exception:
        return empty_delta()


def split_mechanics_block(text: str) -> tuple[str, MechanicsDelta]:
    """Return (visible narration, delta). Visible text never includes the fence."""
    source = text or ""
    idx = source.find(MECHANICS_START)
    if idx >= 0:
        visible = source[:idx].rstrip()
        payload = source[idx + len(MECHANICS_START) :]
        end = payload.find(MECHANICS_END)
        if end >= 0:
            payload = payload[:end]
        return visible.strip(), parse_mechanics_delta(payload)
    # Accidental trailing JSON object (no fence): hide it if it validates as a delta.
    match = re.search(r"\n\s*(\{[\s\S]*\})\s*$", source)
    if match:
        candidate = parse_mechanics_delta(match.group(1))
        if candidate != empty_delta() or match.group(1).strip().startswith("{"):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                return source.strip(), empty_delta()
            if isinstance(data, dict) and any(
                key in data
                for key in ("hp_changes", "conditions", "rest", "resources", "npcs")
            ):
                return source[: match.start()].strip(), parse_mechanics_delta(match.group(1))
    return source.strip(), empty_delta()


class MechanicsStreamFilter:
    """Hide the mechanics fence from live narration tokens."""

    def __init__(self, on_text: Any | None = None) -> None:
        self._on_text = on_text
        self._buf = ""
        self._hidden = False
        self._payload = ""
        self.visible_parts: list[str] = []

    def feed(self, delta: str) -> None:
        if not delta:
            return
        if self._hidden:
            self._payload += delta
            return
        self._buf += delta
        idx = self._buf.find(MECHANICS_START)
        if idx == -1:
            keep = max(0, len(MECHANICS_START) - 1)
            if len(self._buf) > keep:
                emit = self._buf[:-keep]
                self._buf = self._buf[-keep:]
                if emit:
                    self.visible_parts.append(emit)
                    if self._on_text:
                        self._on_text(emit)
            return
        emit = self._buf[:idx]
        if emit:
            self.visible_parts.append(emit)
            if self._on_text:
                self._on_text(emit)
        self._hidden = True
        self._payload = self._buf[idx + len(MECHANICS_START) :]
        self._buf = ""

    def finish(self) -> tuple[str, MechanicsDelta]:
        if not self._hidden and self._buf:
            self.visible_parts.append(self._buf)
            if self._on_text:
                self._on_text(self._buf)
            self._buf = ""
        visible = "".join(self.visible_parts)
        if self._hidden:
            payload = self._payload
            end = payload.find(MECHANICS_END)
            if end >= 0:
                payload = payload[:end]
            return visible.strip(), parse_mechanics_delta(payload)
        return split_mechanics_block(visible)


def _canonical_condition(name: str) -> str | None:
    key = re.sub(r"\s+", " ", (name or "").strip()).lower()
    if key.endswith(" condition"):
        key = key[: -len(" condition")].strip()
    return _CONDITION_BY_KEY.get(key)


def _entity_updates(before: dict, after: dict) -> dict[str, Any]:
    keys = (
        "hp",
        "max_hp",
        "ac",
        "hit_dice_spent",
        "spell_slots",
        "feature_choices",
        "conditions",
        "active_effects",
        "concentration",
        "lay_on_hands_remaining",
        "heroic_inspiration",
        "wild_shape_uses",
        "second_wind_remaining",
        "inventory",
        "currency",
        "savage_attacker_used_this_turn",
        "luck_points_remaining",
        "death_save_successes",
        "death_save_failures",
        "exhaustion",
    )
    updates: dict[str, Any] = {}
    for key in keys:
        if before.get(key) != after.get(key):
            updates[key] = after.get(key)
    return updates


def apply_mechanics_delta(
    character: dict,
    delta: MechanicsDelta | dict | None,
    *,
    pending_rest: dict | None = None,
    pending_cast: dict | None = None,
    combat_active: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Validate the delta against the live sheet and return entity updates plus audit logs."""
    parsed = delta if isinstance(delta, MechanicsDelta) else MechanicsDelta.model_validate(delta or {})
    char = character_from_dict(character)
    before = character_to_dict(char)
    logs: list[str] = []
    refused = set(parsed.refused)

    rest_kind = parsed.rest.kind
    pending_kind = str((pending_rest or {}).get("kind") or "").strip().lower()
    rest_blocked = False
    if combat_active and (rest_kind != "none" or pending_kind in {"short", "long"}):
        logs.append("Rest not applied: combat is still underway.")
        rest_kind = "none"
        rest_blocked = True
    if (
        rest_kind == "none"
        and pending_kind in {"short", "long"}
        and "rest" not in refused
        and not rest_blocked
    ):
        rest_kind = "interrupted"

    rest_applied = False
    if rest_kind == "long" and "rest" not in refused:
        from backend.games.dnd5e.characters.character_builder import long_rest_recover

        rest = long_rest_recover(char)
        logs.append(str(rest.get("summary") or "Long rest."))
        rest_applied = True
    elif rest_kind in {"short", "interrupted"} and "rest" not in refused:
        from backend.games.dnd5e.characters.character_builder import apply_short_rest

        dice = parsed.rest.hit_dice_spent
        if dice is None:
            dice = int((pending_rest or {}).get("dice_to_spend") or 0)
        dice = max(0, int(dice or 0))
        if char.hp >= char.max_hp:
            dice = 0
        rest = apply_short_rest(char, dice_to_spend=dice)
        summary = str(rest.get("summary") or "Short rest.")
        if rest_kind == "interrupted":
            logs.append("Interrupted rest (short-rest benefits).")
            if summary:
                logs.append(summary)
        else:
            logs.append(summary)
        rest_applied = True

    old_hp = int(char.hp or 0)
    max_hp = int(char.max_hp or 0)
    for change in parsed.hp_changes:
        amount = int(change.amount or 0)
        if amount == 0:
            continue
        source = str(change.source or "").strip() or "unspecified"
        if rest_applied and amount > 0:
            src = source.lower()
            if any(token in src for token in ("hit die", "hit dice", "short rest", "rest")):
                continue
        nxt = max(0, min(max_hp, int(char.hp or 0) + amount))
        if amount < 0:
            logs.append(
                f"Took {old_hp - nxt} damage ({source}) (HP {old_hp} -> {nxt}/{max_hp})."
            )
        else:
            logs.append(f"Healed {nxt - old_hp} HP ({source}) (HP {old_hp} -> {nxt}/{max_hp}).")
        char.hp = nxt
        old_hp = nxt

    conditions = [str(item).strip() for item in (char.conditions or []) if str(item).strip()]
    effects = [dict(item) for item in (char.active_effects or []) if isinstance(item, dict)]
    by_effect = {str(item.get("name") or "").strip().lower(): item for item in effects}
    for change in parsed.conditions:
        canonical = _canonical_condition(change.name)
        if not canonical:
            continue
        key = canonical.lower()
        if change.action == "remove":
            conditions = [item for item in conditions if item.lower() != key]
            effects = [item for item in effects if str(item.get("name") or "").lower() != key]
            by_effect.pop(key, None)
            logs.append(f"Condition ended: {canonical}.")
            continue
        if key not in {item.lower() for item in conditions}:
            conditions.append(canonical)
            logs.append(f"Condition gained: {canonical}.")
        prev = by_effect.get(key) or {}
        dc = prev.get("save_dc")
        if not isinstance(dc, int) and isinstance(change.save_dc, int):
            dc = change.save_dc
        source = str(change.source or prev.get("source") or "").strip()
        row = {"name": canonical, "source": source, "save_dc": dc if isinstance(dc, int) else None}
        by_effect[key] = row
        effects = [item for item in effects if str(item.get("name") or "").lower() != key]
        effects.append(row)
        if isinstance(dc, int):
            logs.append(f"{canonical} save DC {dc} ({source or 'source unset'}).")
        from backend.dm.audit import record_audit

        record_audit(
            {
                "event": "condition",
                "source": "mechanics_delta",
                "detail": {
                    "name": canonical,
                    "action": change.action,
                    "save_dc": dc if isinstance(dc, int) else None,
                    "source": source,
                },
            }
        )
    char.conditions = conditions
    char.active_effects = effects

    conc = parsed.concentration
    if conc.action == "end":
        if char.concentration:
            logs.append(f"Concentration ended ({char.concentration}).")
        char.concentration = ""
    elif conc.action == "start" and str(conc.spell or "").strip():
        spell = str(conc.spell).strip()
        char.concentration = spell
        logs.append(f"Concentration: {spell}.")

    spend_loh = max(0, int(parsed.resources.lay_on_hands or 0))
    if spend_loh and char.lay_on_hands_remaining >= 0:
        before_loh = int(char.lay_on_hands_remaining)
        char.lay_on_hands_remaining = max(0, before_loh - spend_loh)
        logs.append(f"Lay on Hands {before_loh} -> {char.lay_on_hands_remaining}.")
        from backend.dm.audit import record_audit

        record_audit(
            {
                "event": "lay_on_hands",
                "source": "mechanics_delta",
                "detail": {
                    "spent": spend_loh,
                    "before": before_loh,
                    "after": int(char.lay_on_hands_remaining),
                },
            }
        )

    spend_hd = max(0, int(parsed.resources.hit_dice or 0))
    if spend_hd and rest_kind == "none":
        available = max(0, char.hit_dice_max - char.hit_dice_spent)
        used = min(available, spend_hd)
        if used:
            char.hit_dice_spent += used
            logs.append(f"Hit Dice spent {used} ({char.hit_dice_max - char.hit_dice_spent}/{char.hit_dice_max} left).")

    if parsed.resources.heroic_inspiration == "grant":
        result = char.grant_heroic_inspiration()
        if result == "granted":
            logs.append("Heroic Inspiration granted.")
    elif parsed.resources.heroic_inspiration == "spend":
        if char.spend_heroic_inspiration():
            logs.append("Heroic Inspiration spent.")

    if parsed.resources.wild_shape and char.wild_shape_uses > 0:
        char.wild_shape_uses -= 1
        logs.append(f"Wild Shape uses now {char.wild_shape_uses}.")

    if parsed.resources.second_wind:
        from backend.games.dnd5e.characters.class_resources import spend_second_wind

        if spend_second_wind(char):
            logs.append("Second Wind used.")

    coins = dict(char.currency or {})
    coin_changed = False
    for key in ("cp", "sp", "ep", "gp", "pp"):
        delta_n = int(getattr(parsed.coins, key) or 0)
        if delta_n:
            coins[key] = max(0, int(coins.get(key) or 0) + delta_n)
            coin_changed = True
    if coin_changed:
        char.currency = coins
        logs.append("Currency updated.")

    inventory = [str(item) for item in (char.inventory or [])]
    for item in parsed.items.add:
        name = str(item).strip()
        if name:
            inventory.append(name)
            logs.append(f"Gained {name}.")
    remove_keys = {str(item).strip().lower() for item in parsed.items.remove if str(item).strip()}
    if remove_keys:
        kept: list[str] = []
        for item in inventory:
            if item.strip().lower() in remove_keys:
                logs.append(f"Lost {item}.")
                continue
            kept.append(item)
        inventory = kept
    char.inventory = inventory

    if "cast" not in refused:
        from backend.games.dnd5e.characters.spell_resources import (
            apply_spell_cast,
            normalize_spell_name,
            spell_level_for,
        )

        casts = list(parsed.spell_casts or [])
        if pending_cast and not casts:
            name = str((pending_cast or {}).get("spell_name") or "").strip()
            if name:
                casts = [
                    SpellCastDelta(
                        spell_name=name,
                        slot_level=int((pending_cast or {}).get("slot_level") or 0),
                        ritual=bool((pending_cast or {}).get("ritual")),
                        free_use=bool((pending_cast or {}).get("free_use")),
                    )
                ]
        conc_spell = str(parsed.concentration.spell or "").strip()
        if parsed.concentration.action == "start" and conc_spell:
            already = {
                normalize_spell_name(item.spell_name) for item in casts if item.spell_name
            }
            if normalize_spell_name(conc_spell) not in already:
                level = spell_level_for(char, conc_spell)
                if level and level > 0:
                    casts.append(SpellCastDelta(spell_name=conc_spell, slot_level=int(level)))
        for cast in casts:
            if cast.refused or not str(cast.spell_name or "").strip():
                if cast.refused:
                    logs.append("Cast not applied: the DM refused the spell.")
                continue
            ok, msg = apply_spell_cast(
                char,
                cast.spell_name,
                slot_level=int(cast.slot_level or 0),
                ritual=bool(cast.ritual),
                free_use=cast.free_use if cast.free_use else None,
                audit_source="mechanics_delta",
                inferred=False,
            )
            logs.append(msg if ok else f"⚠ {msg}")

    char.clamp()
    if not char.ac_manual:
        from backend.games.dnd5e.characters.class_resources import compute_ac_details

        char.ac = int(compute_ac_details(char)["computed"])
    char.conditions = [
        _CONDITION_BY_KEY.get(str(item).strip().lower(), str(item).strip())
        for item in (char.conditions or [])
        if str(item).strip()
    ]
    recanon_effects: list[dict[str, Any]] = []
    seen_effects: set[str] = set()
    for item in char.active_effects or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        key = name.lower()
        if not name or key in seen_effects:
            continue
        seen_effects.add(key)
        recanon_effects.append({**item, "name": _CONDITION_BY_KEY.get(key, name)})
    char.active_effects = recanon_effects
    after = character_to_dict(char)
    updates = _entity_updates(before, after)
    updates["_logs"] = logs
    updates["_npcs"] = [entry.model_dump() for entry in parsed.npcs]
    if parsed.scene_position.strip():
        updates["_scene_position"] = parsed.scene_position.strip()[:200]
    if parsed.reaction_prompt and str(parsed.reaction_prompt.kind or "").strip():
        updates["_reaction_prompt"] = parsed.reaction_prompt.model_dump()
    return updates, logs
