"""Spell slot spending, wild shape uses, and resource tracking."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from backend.characters.character_data import get_class, spells_data
from backend.characters.entity import Dnd5eCharacter
from backend.characters.features import find_subclass_key
from backend.characters.multiclass import class_levels_dict, normalize_class_entries
from backend.config import CURATED_DIR

_SUBCLASS_SPELLS_PATH = CURATED_DIR / "dnd5e_subclass_spells.yaml"


def normalize_spell_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").strip().lower())


@lru_cache(maxsize=1)
def _subclass_spells_data() -> dict[str, Any]:
    if not _SUBCLASS_SPELLS_PATH.is_file():
        return {}
    with _SUBCLASS_SPELLS_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def build_spell_index() -> dict[str, int]:
    """Map normalized spell name -> spell level (0 = cantrip)."""
    index: dict[str, int] = {}
    lists = spells_data().get("spell_lists") or {}
    for _class_id, by_level in lists.items():
        if not isinstance(by_level, dict):
            continue
        for level_key, names in by_level.items():
            if level_key == "cantrips":
                level = 0
            else:
                try:
                    level = int(str(level_key).strip())
                except ValueError:
                    continue
            if not isinstance(names, list):
                continue
            for name in names:
                key = normalize_spell_name(str(name))
                if key and key not in index:
                    index[key] = level
    return index


def _subclass_always_prepared(char: Dnd5eCharacter) -> list[str]:
    subs = _subclass_spells_data()
    names: list[str] = []
    for entry in normalize_class_entries(char):
        cid = entry.get("class_name", "")
        subclass = entry.get("subclass", "")
        key = find_subclass_key(cid, subclass)
        if not key:
            continue
        row = subs.get(key) or {}
        if row.get("class_id") == cid:
            names.extend(str(s) for s in row.get("always_prepared") or [])
    return names


def _char_spell_list_id(char: Dnd5eCharacter) -> str:
    cls = get_class(char.class_name) or {}
    return str(cls.get("spell_list") or char.class_name or "")


def spell_level_for(char: Dnd5eCharacter, spell_name: str) -> int | None:
    key = normalize_spell_name(spell_name)
    if not key:
        return None
    index = build_spell_index()
    if key in index:
        return index[key]
    # Fallback: search class list only
    list_id = _char_spell_list_id(char)
    lists = spells_data().get("spell_lists") or {}
    by_level = lists.get(list_id) or {}
    for level_key, names in by_level.items():
        if level_key == "cantrips":
            level = 0
        else:
            try:
                level = int(str(level_key))
            except ValueError:
                continue
        for name in names or []:
            if normalize_spell_name(str(name)) == key:
                return level
    return None


def is_spell_available(char: Dnd5eCharacter, spell_name: str) -> bool:
    key = normalize_spell_name(spell_name)
    if not key:
        return False
    for group in (
        char.cantrips,
        char.prepared_spells,
        char.known_spells,
        _subclass_always_prepared(char),
    ):
        for name in group:
            if normalize_spell_name(name) == key:
                return True
    return spell_level_for(char, spell_name) is not None


def compute_wild_shape_max(char: Dnd5eCharacter) -> int:
    levels = class_levels_dict(char)
    druid_level = int(levels.get("druid", 0) or 0)
    if druid_level < 2:
        return 0
    return 2


def preserve_remaining_spell_slots(
    previous: dict[str, int],
    maximum: dict[str, int],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for level, max_val in maximum.items():
        lvl = str(level)
        prev = int(previous.get(lvl, max_val) or 0)
        result[lvl] = max(0, min(prev, max_val))
    return result


def sync_wild_shape_uses(char: Dnd5eCharacter) -> None:
    ws_max = compute_wild_shape_max(char)
    if ws_max <= 0:
        char.wild_shape_uses = 0
        return
    char.wild_shape_uses = max(0, min(int(char.wild_shape_uses or 0), ws_max))


def spend_spell_slot(
    char: Dnd5eCharacter,
    spell_level: int,
    *,
    slot_level: int = 0,
) -> tuple[bool, str]:
    """Spend one slot at slot_level (or lowest available >= spell_level)."""
    if spell_level <= 0:
        return True, ""
    need = max(spell_level, slot_level or spell_level)
    slots = dict(char.spell_slots or {})
    if not slots:
        return False, "No spell slots available."
    candidates = sorted(
        (int(k) for k in slots if str(k).isdigit() and int(slots[k]) > 0),
    )
    for lvl in candidates:
        if lvl >= need:
            slots[str(lvl)] = int(slots[str(lvl)]) - 1
            char.spell_slots = slots
            if slot_level and slot_level > spell_level:
                return True, f"Cast at slot level {lvl} (upcast from level {spell_level})."
            return True, f"Spent level {lvl} spell slot."
    return False, f"No level {need}+ spell slots remaining."


def apply_spell_cast(
    char: Dnd5eCharacter,
    spell_name: str,
    *,
    slot_level: int = 0,
    ritual: bool = False,
) -> tuple[bool, str]:
    if not is_spell_available(char, spell_name):
        return False, f"Spell not on character list: {spell_name}"
    level = spell_level_for(char, spell_name)
    if level is None:
        return False, f"Unknown spell level: {spell_name}"
    if level == 0:
        return True, f"Cantrip {spell_name} (no slot spent)."
    if ritual:
        return True, f"Ritual cast {spell_name} (no slot spent)."
    ok, msg = spend_spell_slot(char, level, slot_level=slot_level)
    if ok:
        return True, f"{spell_name}: {msg}"
    return False, f"{spell_name}: {msg}"


def compute_pact_spell_slots(char: Dnd5eCharacter) -> dict[str, int]:
    """Warlock Pact Magic slot pool (recoverable on short rest)."""
    levels = class_levels_dict(char)
    wl = int(levels.get("warlock", 0) or 0)
    if wl <= 0:
        return {}
    cls = get_class("warlock") or {}
    pact = cls.get("pact_slots_by_level") or []
    idx = max(0, min(19, wl - 1))
    row = pact[idx] if pact else {}
    if not isinstance(row, dict):
        return {}
    count = int(row.get("slots", 0) or 0)
    slot_level = int(row.get("level", 1) or 1)
    if count <= 0:
        return {}
    return {str(slot_level): count}


def is_pact_caster(char: Dnd5eCharacter) -> bool:
    return bool(compute_pact_spell_slots(char))


def recover_pact_slots_on_short_rest(char: Dnd5eCharacter) -> str | None:
    """Restore expended Pact Magic slots without affecting other class slots."""
    pact_max = compute_pact_spell_slots(char)
    if not pact_max:
        return None
    from backend.characters.character_builder import compute_spell_slots

    full_max = compute_spell_slots(char)
    slots = dict(char.spell_slots or {})
    restored_parts: list[str] = []
    for lvl, pact_count in pact_max.items():
        before = int(slots.get(lvl, 0) or 0)
        cap = int(full_max.get(lvl, 0) or 0)
        after = min(cap, before + int(pact_count))
        if after > before:
            restored_parts.append(f"L{lvl} {before}→{after}")
        slots[lvl] = after
    char.spell_slots = slots
    if not restored_parts:
        return None
    return f"Pact Magic restored ({', '.join(restored_parts)})."


def apply_resource_updates(
    char: Dnd5eCharacter,
    updates: Any,
) -> tuple[dict[str, Any], list[str]]:
    """Apply resource turn updates to character; return entity_updates dict and log lines."""
    logs: list[str] = []
    entity: dict[str, Any] = {}

    for cast in getattr(updates, "casts", None) or []:
        ok, msg = apply_spell_cast(
            char,
            cast.spell_name,
            slot_level=getattr(cast, "slot_level", 0) or 0,
            ritual=bool(getattr(cast, "ritual", False)),
        )
        if msg:
            logs.append(msg if ok else f"⚠ {msg}")

    if getattr(updates, "end_concentration", False):
        char.concentration = ""
        logs.append("Concentration ended.")
    elif (getattr(updates, "new_concentration", "") or "").strip():
        char.concentration = updates.new_concentration.strip()[:80]
        logs.append(f"Concentrating on {char.concentration}.")

    if getattr(updates, "wild_shape_used", False):
        ws_max = compute_wild_shape_max(char)
        if ws_max <= 0:
            logs.append("⚠ Wild Shape not available for this character.")
        elif char.wild_shape_uses <= 0:
            logs.append("⚠ No Wild Shape uses remaining.")
        else:
            char.wild_shape_uses -= 1
            logs.append(f"Wild Shape used ({char.wild_shape_uses}/{ws_max} remaining).")

    entity["spell_slots"] = dict(char.spell_slots)
    entity["concentration"] = char.concentration
    entity["wild_shape_uses"] = char.wild_shape_uses
    return entity, logs
