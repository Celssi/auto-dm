"""Spell slot spending, wild shape uses, and resource tracking."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR
from backend.dm.audit import character_audit_slice, record_audit
from backend.games.dnd5e.characters.character_data import find_third_caster, get_class, spells_data
from backend.games.dnd5e.characters.entity import Dnd5eCharacter
from backend.games.dnd5e.characters.features import find_subclass_key
from backend.games.dnd5e.characters.multiclass import class_levels_dict, normalize_class_entries

_SUBCLASS_SPELLS_PATH = CURATED_DIR / "dnd5e_subclass_spells.yaml"


_SPELL_TRAILING_JUNK = re.compile(
    r"[\s,;:]+("
    r"last slot|with a slot|using a slot|spend(ing)? a slot|"
    r"at \d+(st|nd|rd|th)?-?level|slot \d+|"
    r"free( use)?|no slot|without a slot|magic initiate"
    r").*$",
    re.IGNORECASE,
)


def normalize_spell_name(name: str) -> str:
    text = (name or "").strip().lower().replace("armour", "armor")
    text = _SPELL_TRAILING_JUNK.sub("", text)
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    return re.sub(r"[^a-z0-9]+", "", text)


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
    for entry in normalize_class_entries(char):
        cid = str(entry.get("class_name") or "").lower()
        sub = str(entry.get("subclass") or char.subclass or "")
        tc = find_third_caster(cid, sub)
        if tc:
            return str(tc.get("spell_list") or "wizard")
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


def character_spell_groups(char: Dnd5eCharacter) -> list[list[str]]:
    fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
    mi: list[str] = []
    for key in ("magic_initiate_level1", "magic_initiate_cantrips"):
        val = fc.get(key)
        if isinstance(val, list):
            mi.extend(str(item) for item in val if str(item).strip())
        elif val:
            mi.append(str(val))
    return [
        list(char.cantrips or []),
        list(char.prepared_spells or []),
        list(char.known_spells or []),
        list(char.spellbook or []),
        _subclass_always_prepared(char),
        mi,
    ]


def match_spell_name(char: Dnd5eCharacter | None, raw: str) -> str | None:
    """Resolve a player/DM spell mention to a canonical name on the sheet or index."""
    key = normalize_spell_name(raw)
    if not key:
        return None
    groups = character_spell_groups(char) if char is not None else []
    for group in groups:
        for name in group:
            if normalize_spell_name(name) == key:
                return str(name).strip()
    index = build_spell_index()
    if key in index:
        return str(raw).strip()
    contained = [idx_key for idx_key in index if idx_key and idx_key in key]
    if contained:
        best = max(contained, key=len)
        if char is not None:
            for group in groups:
                for name in group:
                    if normalize_spell_name(name) == best:
                        return str(name).strip()
        return best
    return None


def is_spell_available(char: Dnd5eCharacter, spell_name: str) -> bool:
    resolved = match_spell_name(char, spell_name)
    if resolved:
        return True
    key = normalize_spell_name(spell_name)
    if not key:
        return False
    return spell_level_for(char, spell_name) is not None


def _has_magic_initiate(char: Dnd5eCharacter) -> bool:
    feat = str(char.origin_feat or "").strip().lower()
    versatile = str(char.versatile_origin_feat or "").strip().lower()
    return "magic initiate" in feat or "magic initiate" in versatile


def magic_initiate_spell_name(char: Dnd5eCharacter) -> str:
    fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
    return str(fc.get("magic_initiate_level1") or "").strip()


def magic_initiate_free_used(char: Dnd5eCharacter) -> bool:
    fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
    return bool(fc.get("_magic_initiate_free_used"))


def magic_initiate_free_available(
    char: Dnd5eCharacter,
    spell_name: str,
    *,
    requested_free: bool = False,
) -> bool:
    if magic_initiate_free_used(char) or not _has_magic_initiate(char):
        return False
    level = spell_level_for(char, spell_name)
    if level != 1:
        return False
    mi_spell = magic_initiate_spell_name(char)
    if mi_spell and normalize_spell_name(mi_spell) == normalize_spell_name(spell_name):
        return True
    if requested_free and not mi_spell:
        return is_spell_available(char, spell_name)
    return False


def mark_magic_initiate_free_used(char: Dnd5eCharacter, spell_name: str = "") -> None:
    fc = dict(char.feature_choices or {})
    if spell_name.strip() and not str(fc.get("magic_initiate_level1") or "").strip():
        fc["magic_initiate_level1"] = spell_name.strip()
    fc["_magic_initiate_free_used"] = True
    char.feature_choices = fc


def set_mage_armor_active(char: Dnd5eCharacter, active: bool) -> None:
    fc = dict(char.feature_choices or {})
    if active:
        fc["_mage_armor_active"] = True
    else:
        fc.pop("_mage_armor_active", None)
    char.feature_choices = fc


def mage_armor_active(char: Dnd5eCharacter) -> bool:
    fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
    if fc.get("_mage_armor_active"):
        return True
    return any(str(item).strip().lower() == "mage armor" for item in (char.conditions or []))


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
    audit_source: str = "spell_resources",
    inferred: bool = False,
) -> tuple[bool, str]:
    """Spend one slot at slot_level (or lowest available >= spell_level)."""
    if spell_level <= 0:
        return True, ""
    need = max(spell_level, slot_level or spell_level)
    slots = dict(char.spell_slots or {})
    if not slots:
        return False, "No spell slots available."
    before_slice = character_audit_slice(character_to_dict_for_audit(char))
    candidates = sorted(
        (int(k) for k in slots if str(k).isdigit() and int(slots[k]) > 0),
    )
    for lvl in candidates:
        if lvl >= need:
            slots[str(lvl)] = int(slots[str(lvl)]) - 1
            char.spell_slots = slots
            after_slice = character_audit_slice(character_to_dict_for_audit(char))
            record_audit(
                {
                    "event": "spell_slot",
                    "source": audit_source,
                    "before": before_slice,
                    "after": after_slice,
                    "detail": {
                        "slot_level": lvl,
                        "spell_level": spell_level,
                        "inferred": inferred,
                    },
                }
            )
            if slot_level and slot_level > spell_level:
                return True, f"Cast at slot level {lvl} (upcast from level {spell_level})."
            return True, f"Spent level {lvl} spell slot."
    return False, f"No level {need}+ spell slots remaining."


def character_to_dict_for_audit(char: Dnd5eCharacter) -> dict[str, Any]:
    from backend.games.dnd5e.characters.entity import character_to_dict

    return character_to_dict(char)


def apply_spell_cast(
    char: Dnd5eCharacter,
    spell_name: str,
    *,
    slot_level: int = 0,
    ritual: bool = False,
    audit_source: str = "spell_resources",
    inferred: bool = False,
    free_use: bool | None = None,
    requested_text: str = "",
) -> tuple[bool, str]:
    resolved = match_spell_name(char, spell_name) or str(spell_name or "").strip()
    if not str(resolved or spell_name or "").strip():
        return False, ""
    if not is_spell_available(char, resolved or spell_name):
        return False, f"Spell not on character list: {spell_name}"
    level = spell_level_for(char, resolved)
    if level is None:
        return False, f"Unknown spell level: {spell_name}"
    display = " ".join(part.capitalize() for part in str(resolved or spell_name).replace("_", " ").split())
    if normalize_spell_name(display) == "magearmor" and mage_armor_active(char):
        return False, "Mage Armor is already active (no slot spent)."
    if level == 0:
        record_audit(
            {
                "event": "spell_cast",
                "source": audit_source,
                "detail": {
                    "spell": display,
                    "level": 0,
                    "ritual": False,
                    "cantrip": True,
                    "inferred": inferred,
                },
            }
        )
        return True, f"Cantrip {display} (no slot spent)."
    if ritual:
        record_audit(
            {
                "event": "spell_cast",
                "source": audit_source,
                "detail": {
                    "spell": display,
                    "level": level,
                    "ritual": True,
                    "inferred": inferred,
                },
            }
        )
        return True, f"Ritual cast {display} (no slot spent)."
    text = (requested_text or "").lower()
    wants_slot = "with a slot" in text or "last slot" in text or "using a slot" in text
    requested_free = bool(free_use) or (
        not wants_slot
        and any(
            token in text
            for token in ("magic initiate", "free use", "free cast", "no slot", "without a slot")
        )
    )
    use_free = False
    if not wants_slot:
        if free_use is False:
            use_free = False
        elif requested_free:
            use_free = magic_initiate_free_available(char, display, requested_free=True)
        else:
            use_free = magic_initiate_free_available(char, display, requested_free=False)
    if use_free:
        mark_magic_initiate_free_used(char, display)
        if normalize_spell_name(display) == "magearmor":
            set_mage_armor_active(char, True)
        record_audit(
            {
                "event": "spell_cast",
                "source": audit_source,
                "detail": {
                    "spell": display,
                    "level": level,
                    "ritual": False,
                    "magic_initiate_free": True,
                    "inferred": inferred,
                },
            }
        )
        return True, f"{display}: Magic Initiate free cast (no slot spent)."
    ok, msg = spend_spell_slot(
        char,
        level,
        slot_level=slot_level,
        audit_source=audit_source,
        inferred=inferred,
    )
    if ok:
        if normalize_spell_name(display) == "magearmor":
            set_mage_armor_active(char, True)
        record_audit(
            {
                "event": "spell_cast",
                "source": audit_source,
                "detail": {
                    "spell": display,
                    "level": level,
                    "slot_level": slot_level or level,
                    "ritual": False,
                    "inferred": inferred,
                },
            }
        )
        return True, f"{display}: {msg}"
    return False, f"{display}: {msg}"


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
    from backend.games.dnd5e.characters.character_builder import compute_spell_slots

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


def recover_arcane_recovery(char: Dnd5eCharacter) -> str | None:
    """Wizard Arcane Recovery: restore slots totaling half wizard level (round up)."""
    levels = class_levels_dict(char)
    wizard_level = int(levels.get("wizard", 0) or 0)
    if wizard_level <= 0:
        return None
    fc = dict(char.feature_choices or {})
    if fc.get("_arcane_recovery_used"):
        return None
    from backend.games.dnd5e.characters.character_builder import compute_spell_slots

    budget = (wizard_level + 1) // 2
    max_slot = min(5, budget)
    max_slots = compute_spell_slots(char)
    slots = dict(char.spell_slots or {})
    recovered: list[int] = []
    remaining = budget
    for lvl in range(max_slot, 0, -1):
        key = str(lvl)
        cap = int(max_slots.get(key, 0) or 0)
        current = int(slots.get(key, 0) or 0)
        missing = max(0, cap - current)
        while missing > 0 and remaining >= lvl:
            current += 1
            missing -= 1
            remaining -= lvl
            recovered.append(lvl)
            slots[key] = current
    if not recovered:
        return None
    char.spell_slots = slots
    fc["_arcane_recovery_used"] = True
    char.feature_choices = fc
    parts = ", ".join(f"L{n}" for n in recovered)
    return f"Arcane Recovery restored {len(recovered)} slot(s) ({parts})."


def apply_resource_updates(
    char: Dnd5eCharacter,
    updates: Any,
    *,
    audit_source: str = "resource_keeper",
    inferred: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    """Apply resource turn updates to character; return entity_updates dict and log lines."""
    logs: list[str] = []
    entity: dict[str, Any] = {}
    before_slice = character_audit_slice(character_to_dict_for_audit(char))

    for cast in getattr(updates, "casts", None) or []:
        spell_name = str(getattr(cast, "spell_name", "") or "").strip()
        if not spell_name:
            continue
        ok, msg = apply_spell_cast(
            char,
            spell_name,
            slot_level=getattr(cast, "slot_level", 0) or 0,
            ritual=bool(getattr(cast, "ritual", False)),
            audit_source=audit_source,
            inferred=inferred,
            free_use=getattr(cast, "free_use", None),
            requested_text=str(getattr(cast, "requested_text", "") or ""),
        )
        if msg:
            logs.append(msg if ok else f"⚠ {msg}")

    if getattr(updates, "end_concentration", False):
        char.concentration = ""
        logs.append("Concentration ended.")
        record_audit(
            {
                "event": "concentration",
                "source": audit_source,
                "before": before_slice,
                "after": character_audit_slice(character_to_dict_for_audit(char)),
                "detail": {"ended": True, "inferred": inferred},
            }
        )
    elif (getattr(updates, "new_concentration", "") or "").strip():
        char.concentration = updates.new_concentration.strip()[:80]
        logs.append(f"Concentrating on {char.concentration}.")
        record_audit(
            {
                "event": "concentration",
                "source": audit_source,
                "before": before_slice,
                "after": character_audit_slice(character_to_dict_for_audit(char)),
                "detail": {"spell": char.concentration, "started": True, "inferred": inferred},
            }
        )

    if getattr(updates, "wild_shape_used", False):
        ws_max = compute_wild_shape_max(char)
        if ws_max <= 0:
            logs.append("⚠ Wild Shape not available for this character.")
        elif char.wild_shape_uses <= 0:
            logs.append("⚠ No Wild Shape uses remaining.")
        else:
            char.wild_shape_uses -= 1
            logs.append(f"Wild Shape used ({char.wild_shape_uses}/{ws_max} remaining).")
            record_audit(
                {
                    "event": "wild_shape",
                    "source": audit_source,
                    "before": before_slice,
                    "after": character_audit_slice(character_to_dict_for_audit(char)),
                    "detail": {"uses": char.wild_shape_uses, "max": ws_max, "inferred": inferred},
                }
            )

    entity["spell_slots"] = dict(char.spell_slots)
    entity["concentration"] = char.concentration
    entity["wild_shape_uses"] = char.wild_shape_uses
    entity["feature_choices"] = dict(char.feature_choices or {})
    if not char.ac_manual:
        from backend.games.dnd5e.characters.class_resources import compute_ac_details

        char.ac = int(compute_ac_details(char)["computed"])
        entity["ac"] = char.ac
    return entity, logs
