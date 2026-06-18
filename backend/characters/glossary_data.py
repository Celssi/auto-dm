"""Load curated glossary entries (spells, skills, feats) for UI tooltips."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR
from backend.characters.spell_resources import normalize_spell_name

_GLOSSARY_PATH = CURATED_DIR / "dnd5e_glossary.yaml"


def _load() -> dict[str, Any]:
    if not _GLOSSARY_PATH.exists():
        return {}
    raw = _GLOSSARY_PATH.read_text(encoding="utf-8")
    if raw.lstrip().startswith("#"):
        raw = re.sub(r"^#.*\n", "", raw, count=0, flags=re.MULTILINE)
    return yaml.safe_load(raw) or {}


@lru_cache(maxsize=1)
def glossary_data() -> dict[str, Any]:
    return _load()


def _spell_summary(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    if entry.get("casting_time"):
        parts.append(f"Casting Time: {entry['casting_time']}")
    if entry.get("range"):
        parts.append(f"Range: {entry['range']}")
    if entry.get("components"):
        parts.append(f"Components: {entry['components']}")
    if entry.get("duration"):
        parts.append(f"Duration: {entry['duration']}")
    meta = ". ".join(parts)
    text = str(entry.get("text") or "").strip()
    return f"{meta}.\n\n{text}" if meta and text else text or meta


def _skill_summary(entry: dict[str, Any]) -> str:
    ab = str(entry.get("ability") or "").upper()
    text = str(entry.get("text") or "").strip()
    if ab and text:
        return f"{ab} skill. {text}"
    return text


def _feat_summary(entry: dict[str, Any]) -> str:
    cat = str(entry.get("category") or "").strip()
    text = str(entry.get("text") or "").strip()
    return f"{cat}. {text}" if cat else text


def _feature_summary(entry: dict[str, Any]) -> str:
    text = str(entry.get("text") or "").strip()
    level = entry.get("level")
    if level is not None and text:
        return f"Level {level} class feature. {text}"
    return text


def glossary_db_index() -> dict[str, dict[str, Any]]:
    """Flat lookup index keyed by normalize_spell_name(id/title)."""
    data = glossary_data()
    index: dict[str, dict[str, Any]] = {}

    for key, row in (data.get("spells") or {}).items():
        if not isinstance(row, dict):
            continue
        nk = normalize_spell_name(str(key))
        index[nk] = {
            "kind": "spell",
            "title": row.get("title") or key,
            "summary": _spell_summary(row),
            "level": row.get("level"),
        }

    for key, row in (data.get("skills") or {}).items():
        if not isinstance(row, dict):
            continue
        nk = normalize_spell_name(str(key))
        index[nk] = {
            "kind": "skill",
            "title": row.get("title") or key,
            "summary": _skill_summary(row),
        }

    for key, row in (data.get("feats") or {}).items():
        if not isinstance(row, dict):
            continue
        nk = normalize_spell_name(str(key))
        index[nk] = {
            "kind": "feat",
            "title": row.get("title") or key,
            "summary": _feat_summary(row),
        }

    for key, row in (data.get("features") or {}).items():
        if not isinstance(row, dict):
            continue
        nk = normalize_spell_name(str(key))
        index[nk] = {
            "kind": "feature",
            "title": row.get("title") or key,
            "summary": _feature_summary(row),
            "level": row.get("level"),
        }

    return index
