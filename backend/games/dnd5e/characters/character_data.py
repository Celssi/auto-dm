"""Load D&D 5e curated character creation data."""

from __future__ import annotations

import copy
from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR
from backend.games.dnd5e.characters.entity import CAMPAIGN_SETTING_OPTIONS

_SKILLS_PATH = CURATED_DIR / "dnd5e_skills.yaml"
_CLASSES_PATH = CURATED_DIR / "dnd5e_classes.yaml"
_SPECIES_PATH = CURATED_DIR / "dnd5e_species.yaml"
_BACKGROUNDS_PATH = CURATED_DIR / "dnd5e_backgrounds.yaml"
_SPELLS_PATH = CURATED_DIR / "dnd5e_spells.yaml"
_EQUIPMENT_PATH = CURATED_DIR / "dnd5e_equipment.yaml"
_FAERUN_PATH = CURATED_DIR / "dnd5e_faerun.yaml"


def _load(path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def skills_data() -> dict[str, Any]:
    return _load(_SKILLS_PATH)


@lru_cache(maxsize=1)
def classes_data() -> dict[str, Any]:
    return _load(_CLASSES_PATH)


@lru_cache(maxsize=1)
def species_data() -> dict[str, Any]:
    return _load(_SPECIES_PATH)


@lru_cache(maxsize=1)
def backgrounds_data() -> dict[str, Any]:
    return _load(_BACKGROUNDS_PATH)


@lru_cache(maxsize=1)
def spells_data() -> dict[str, Any]:
    return _load(_SPELLS_PATH)


@lru_cache(maxsize=1)
def equipment_data() -> dict[str, Any]:
    return _load(_EQUIPMENT_PATH)


def _is_gear_starting_package(package: dict[str, Any]) -> bool:
    """Drop gold-only PHB options (e.g. fighter C: 155 GP)."""
    if not isinstance(package, dict):
        return False
    has_items = bool(package.get("items") or package.get("weapons") or package.get("armor"))
    return has_items


def list_starting_gear_options(class_id: str) -> list[dict[str, Any]]:
    """Gear-only starting packages for a class (never gold-only alternatives)."""
    key = str(class_id or "").strip().lower()
    if not key:
        return []
    data = equipment_data()
    options = (data.get("class_starting_gear_options") or {}).get(key) or []
    filtered = [o for o in options if _is_gear_starting_package(o)]
    if filtered:
        return filtered
    legacy = (data.get("class_starting_gear") or {}).get(key)
    if isinstance(legacy, dict) and _is_gear_starting_package(legacy):
        return [{"id": "standard", "label": "Standard kit", **legacy}]
    return []


@lru_cache(maxsize=1)
def faerun_data() -> dict[str, Any]:
    if not _FAERUN_PATH.exists():
        return {}
    return _load(_FAERUN_PATH)


def _merge_class_extensions(classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extensions = faerun_data().get("class_extensions") or {}
    if not extensions:
        return classes
    merged: list[dict[str, Any]] = []
    for row in classes:
        item = copy.deepcopy(row)
        ext = extensions.get(item.get("id") or "")
        if isinstance(ext, dict):
            extra = ext.get("subclasses") or []
            existing = list(item.get("subclasses") or [])
            for sub in extra:
                label = str(sub)
                if label and label not in existing:
                    existing.append(label)
            item["subclasses"] = existing
            if extra:
                item["faerun_subclasses"] = list(extra)
        merged.append(item)
    return merged


def _faerun_backgrounds() -> list[dict[str, Any]]:
    return list(faerun_data().get("backgrounds") or [])


def list_armor() -> list[dict[str, Any]]:
    return list(equipment_data().get("armor") or [])


def get_armor(armor_id: str) -> dict[str, Any] | None:
    for row in list_armor():
        if row.get("id") == armor_id:
            return row
    return None


def list_weapons() -> list[dict[str, Any]]:
    return list(equipment_data().get("weapons") or [])


def get_weapon(weapon_id: str) -> dict[str, Any] | None:
    wid = str(weapon_id or "").strip().lower()
    for row in list_weapons():
        if str(row.get("id") or "").lower() == wid:
            return row
    return None


def list_background_gear_options(background_id: str) -> list[dict[str, Any]]:
    key = str(background_id or "").strip().lower()
    if not key:
        return []
    return list((equipment_data().get("background_starting_gear_options") or {}).get(key) or [])


def list_languages() -> list[str]:
    return [str(x) for x in (equipment_data().get("languages") or [])]


def shield_ac_bonus() -> int:
    return int(equipment_data().get("shield_ac", 2) or 2)


def list_classes(*, include_faerun: bool = True) -> list[dict[str, Any]]:
    core = list(classes_data().get("classes") or [])
    if not include_faerun:
        return core
    return _merge_class_extensions(core)


def list_species() -> list[dict[str, Any]]:
    return list(species_data().get("species") or [])


def list_backgrounds(*, include_faerun: bool = True) -> list[dict[str, Any]]:
    core = list(backgrounds_data().get("backgrounds") or [])
    if not include_faerun:
        return core
    return core + _faerun_backgrounds()


def get_class(class_id: str) -> dict[str, Any] | None:
    for row in list_classes(include_faerun=True):
        if row.get("id") == class_id:
            return row
    return None


def get_species(species_id: str) -> dict[str, Any] | None:
    for row in list_species():
        if row.get("id") == species_id:
            return row
    return None


def get_background(background_id: str) -> dict[str, Any] | None:
    for row in list_backgrounds(include_faerun=True):
        if row.get("id") == background_id:
            return row
    return None


def spell_list_for(class_id: str) -> dict[str, list[str]]:
    lists = dict(spells_data().get("spell_lists") or {})
    cls = get_class(class_id) or {}
    key = str(cls.get("spell_list") or class_id)
    raw = lists.get(key) or {}
    return {str(k): list(v or []) for k, v in raw.items() if isinstance(v, list)}


def full_caster_slots(level: int) -> dict[str, int]:
    table = classes_data().get("full_caster_slots") or {}
    row = table.get(str(max(1, min(20, int(level)))))
    if not isinstance(row, list):
        return {}
    return {str(i + 1): int(v) for i, v in enumerate(row) if int(v or 0) > 0}


def half_caster_slots(level: int) -> dict[str, int]:
    table = classes_data().get("half_caster_slots") or {}
    row = table.get(str(max(1, min(20, int(level)))))
    if not isinstance(row, list):
        return {}
    return {str(i + 1): int(v) for i, v in enumerate(row) if int(v or 0) > 0}


def multiclass_prerequisites(class_id: str) -> dict[str, int]:
    from backend.games.dnd5e.characters.multiclass import multiclass_prerequisites as _mp

    return _mp(class_id)


def character_options_payload(*, include_faerun: bool = False) -> dict[str, Any]:
    from backend.games.dnd5e.characters.creation_choices import (
        creation_choices_catalog,
        weapon_mastery_data,
    )

    skills = skills_data()
    faerun = faerun_data()
    backgrounds = list_backgrounds(include_faerun=include_faerun)
    classes = list_classes(include_faerun=include_faerun)
    return {
        "classes": classes,
        "species": list_species(),
        "backgrounds": backgrounds,
        "skills": skills.get("skills") or [],
        "alignments": skills.get("alignments") or [],
        "standard_array": skills.get("standard_array") or [15, 14, 13, 12, 10, 8],
        "standard_array_by_class": skills.get("standard_array_by_class") or {},
        "spell_lists": spells_data().get("spell_lists") or {},
        "campaign_settings": CAMPAIGN_SETTING_OPTIONS,
        "armor": list_armor(),
        "weapons": list_weapons(),
        "languages": list_languages(),
        "shield_ac": shield_ac_bonus(),
        "starting_gear_options": equipment_data().get("class_starting_gear_options") or {},
        "background_starting_gear_options": equipment_data().get("background_starting_gear_options")
        or {},
        "creation_choice_catalog": creation_choices_catalog(include_faerun=include_faerun),
        "weapon_mastery_properties": weapon_mastery_data().get("properties") or {},
        "include_faerun": include_faerun,
        "faerun_available": bool(faerun),
        "faerun": {
            "label": faerun.get("label", "Heroes of Faerûn"),
            "background_count": len(_faerun_backgrounds()),
            "subclass_extensions": list((faerun.get("class_extensions") or {}).keys()),
            "regional_equipment": list((faerun.get("equipment") or {}).get("regional_items") or []),
            "spell_names": list(faerun.get("spell_names") or []),
        }
        if include_faerun and faerun
        else None,
    }
