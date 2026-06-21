"""Class and subclass feature lookup from curated YAML."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from backend.characters.entity import Dnd5eCharacter
from backend.characters.multiclass import normalize_class_entries, slugify
from backend.config import CURATED_DIR

_CLASS_FEATURES_PATH = CURATED_DIR / "dnd5e_class_features.yaml"
_SUBCLASS_FEATURES_PATH = CURATED_DIR / "dnd5e_subclass_features.yaml"


@lru_cache(maxsize=1)
def class_features_data() -> dict[str, Any]:
    if not _CLASS_FEATURES_PATH.exists():
        return {}
    with _CLASS_FEATURES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def subclass_features_data() -> dict[str, Any]:
    if not _SUBCLASS_FEATURES_PATH.exists():
        return {}
    with _SUBCLASS_FEATURES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _features_at_level(table: dict[str, list] | None, level: int) -> list[str]:
    if not isinstance(table, dict):
        return []
    row = table.get(str(level)) or table.get(level)
    if isinstance(row, list):
        return [str(x) for x in row if str(x).strip() and str(x) != "—"]
    return []


def class_features_for(class_id: str, level: int) -> list[str]:
    classes = class_features_data().get("classes") or {}
    table = classes.get(class_id) or {}
    return _features_at_level(table, level)


def find_subclass_key(class_id: str, subclass_label: str) -> str | None:
    label = str(subclass_label or "").strip()
    if not label:
        return None
    subs = subclass_features_data().get("subclasses") or {}
    slug = slugify(label)
    if slug in subs and subs[slug].get("class_id") == class_id:
        return slug
    for key, row in subs.items():
        if not isinstance(row, dict):
            continue
        if row.get("class_id") != class_id:
            continue
        if slugify(str(row.get("label", ""))) == slug or key == slug:
            return key
    return slug if slug in subs else None


def subclass_features_for(class_id: str, subclass_label: str, level: int) -> list[str]:
    key = find_subclass_key(class_id, subclass_label)
    if not key:
        return []
    row = (subclass_features_data().get("subclasses") or {}).get(key) or {}
    table = row.get("features") or {}
    return _features_at_level(table, level)


def unlocked_features(char: Dnd5eCharacter) -> dict[str, Any]:
    """All class and subclass features unlocked at current levels."""
    from backend.characters.creation_choices import (
        class_choice_lines,
        resolved_choice_lines,
        species_trait_lines,
    )
    from backend.characters.origin_feats import origin_feat_passive_lines

    class_feats: dict[str, list[str]] = {}
    subclass_feats: dict[str, list[str]] = {}
    for entry in normalize_class_entries(char):
        cid = entry["class_name"]
        lv = int(entry["level"])
        cls_list: list[str] = []
        sub_list: list[str] = []
        for level in range(1, lv + 1):
            cls_list.extend(class_features_for(cid, level))
            sub = str(entry.get("subclass") or "")
            if sub:
                sub_list.extend(subclass_features_for(cid, sub, level))
        if cls_list:
            class_feats[cid] = cls_list
        if sub_list:
            key = f"{cid}:{entry.get('subclass')}"
            subclass_feats[key] = sub_list
    return {
        "class_features": class_feats,
        "subclass_features": subclass_feats,
        "species_traits": species_trait_lines(char),
        "origin_feat_effects": origin_feat_passive_lines(char),
        "resolved_choices": class_choice_lines(char),
        "all_creation_choices": resolved_choice_lines(char),
    }


def features_summary_lines(char: Dnd5eCharacter) -> list[str]:
    unlocked = unlocked_features(char)
    lines: list[str] = []
    for cid, feats in unlocked["class_features"].items():
        lines.append(f"{cid.title()} features: {', '.join(feats)}")
    for key, feats in unlocked["subclass_features"].items():
        lines.append(f"{key}: {', '.join(feats)}")
    return lines
