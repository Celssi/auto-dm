"""Multiclass rules and class level helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from backend.characters.character_data import full_caster_slots, get_class
from backend.characters.entity import ABILITY_KEYS, Dnd5eCharacter
from backend.config import CURATED_DIR

_MULTICLASS_PATH = CURATED_DIR / "dnd5e_multiclass.yaml"


@lru_cache(maxsize=1)
def multiclass_data() -> dict[str, Any]:
    if not _MULTICLASS_PATH.exists():
        return {}
    with _MULTICLASS_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def slugify(name: str) -> str:
    return (
        str(name or "")
        .lower()
        .replace("'s", "")
        .replace("'", "")
        .replace("—", "")
        .replace("/", "_")
        .replace(" ", "_")
        .strip("_")
    )


def normalize_class_entries(char: Dnd5eCharacter) -> list[dict[str, Any]]:
    """Return [{class_name, level, subclass, class_skill_choices}, ...]."""
    raw = char.classes if isinstance(char.classes, list) else []
    entries: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("class_name") or "").strip().lower()
        lv = int(item.get("level", 0) or 0)
        if not cid or lv <= 0:
            continue
        entries.append(
            {
                "class_name": cid,
                "level": lv,
                "subclass": str(item.get("subclass") or "").strip(),
                "class_skill_choices": list(item.get("class_skill_choices") or []),
            }
        )
    if entries:
        return entries
    if char.class_name:
        return [
            {
                "class_name": char.class_name,
                "level": char.level,
                "subclass": char.subclass,
                "class_skill_choices": list(char.class_skill_choices or []),
            }
        ]
    return []


def class_levels_dict(char: Dnd5eCharacter) -> dict[str, int]:
    levels: dict[str, int] = {}
    for entry in normalize_class_entries(char):
        cid = entry["class_name"]
        levels[cid] = levels.get(cid, 0) + int(entry["level"])
    return levels


def total_class_level(char: Dnd5eCharacter) -> int:
    return min(20, sum(class_levels_dict(char).values()))


def primary_class_entry(char: Dnd5eCharacter) -> dict[str, Any] | None:
    entries = normalize_class_entries(char)
    if not entries:
        return None
    return max(entries, key=lambda e: int(e.get("level", 0)))


def sync_legacy_class_fields(char: Dnd5eCharacter) -> None:
    """Keep class_name/level/subclass aligned with class entries."""
    entries = normalize_class_entries(char)
    char.classes = entries
    total = total_class_level(char)
    char.level = max(1, total) if total else char.level
    primary = primary_class_entry(char)
    if primary:
        char.class_name = primary["class_name"]
        char.subclass = str(primary.get("subclass") or "")
        char.class_skill_choices = list(primary.get("class_skill_choices") or [])
        cls = get_class(char.class_name)
        if cls:
            char.hit_die = int(cls.get("hit_die", char.hit_die) or char.hit_die)


def multiclass_prerequisites(class_id: str) -> dict[str, int]:
    row = (multiclass_data().get("classes") or {}).get(class_id) or {}
    return dict(row.get("prerequisites") or {})


def can_multiclass_into(char: Dnd5eCharacter, class_id: str) -> tuple[bool, str]:
    reqs = multiclass_prerequisites(class_id)
    if not reqs:
        return True, ""
    scores = char.ability_scores or {}
    # Fighter-style OR: if multiple abilities listed, need ANY one at minimum
    if class_id == "fighter" and "str" in reqs and "dex" in reqs:
        if scores.get("str", 10) >= reqs["str"] or scores.get("dex", 10) >= reqs["dex"]:
            return True, ""
        return False, "Requires STR 13 or DEX 13"
    for ab, minimum in reqs.items():
        if ab not in ABILITY_KEYS:
            continue
        if int(scores.get(ab, 10) or 10) < int(minimum):
            return False, f"Requires {ab.upper()} {minimum}"
    return True, ""


def effective_caster_level(levels: dict[str, int]) -> int:
    data = multiclass_data()
    full = set(data.get("full_casters") or [])
    half = set(data.get("half_casters") or [])
    total = 0
    for cid, lv in levels.items():
        if lv <= 0:
            continue
        cls = get_class(cid) or {}
        if cls.get("spellcasting") == "pact":
            continue
        if cid in half:
            total += lv // 2
        elif cid in full or cls.get("spellcasting"):
            total += lv
    return total


def compute_multiclass_spell_slots(char: Dnd5eCharacter) -> dict[str, int]:
    levels = class_levels_dict(char)
    if len(levels) <= 1:
        return {}
    caster_lv = effective_caster_level(levels)
    slots: dict[str, int] = {}
    if caster_lv > 0:
        slots = full_caster_slots(caster_lv)
    wl = levels.get("warlock", 0)
    if wl > 0:
        cls = get_class("warlock") or {}
        pact = cls.get("pact_slots_by_level") or []
        idx = max(0, min(19, wl - 1))
        row = pact[idx] if pact else {}
        if isinstance(row, dict):
            count = int(row.get("slots", 0) or 0)
            slot_level = int(row.get("level", 1) or 1)
            if count > 0:
                key = str(slot_level)
                slots[key] = slots.get(key, 0) + count
    return slots


def hit_dice_pool(char: Dnd5eCharacter) -> dict[str, int]:
    """Hit dice by die size, e.g. {'10': 5, '6': 2}."""
    pool: dict[str, int] = {}
    for cid, lv in class_levels_dict(char).items():
        cls = get_class(cid) or {}
        die = int(cls.get("hit_die", 8) or 8)
        pool[str(die)] = pool.get(str(die), 0) + lv
    return pool


def asi_feat_slots_multiclass(char: Dnd5eCharacter) -> int:
    from backend.characters.character_builder import asi_feat_slots

    total = 0
    for cid, lv in class_levels_dict(char).items():
        total += asi_feat_slots(cid, lv)
    return total
