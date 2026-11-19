"""Curated 2024 rules lookup used before RAG."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR
from backend.games.dnd5e.characters.character_data import get_weapon, list_weapons
from backend.games.dnd5e.characters.creation_choices import weapon_mastery_data
from backend.games.dnd5e.characters.spell_resources import normalize_spell_name

_RULES_PATH = CURATED_DIR / "dnd5e_rules_glossary.yaml"
_MASTERY_NAMES = ("cleave", "graze", "nick", "push", "sap", "slow", "topple", "vex")


@lru_cache(maxsize=1)
def rules_glossary() -> dict[str, Any]:
    if not _RULES_PATH.is_file():
        return {}
    data = yaml.safe_load(_RULES_PATH.read_text(encoding="utf-8")) or {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def rewrite_rules_query(message: str) -> str:
    """Turn a play utterance into a 2024 rules search string."""
    lower = (message or "").lower()
    extras: list[str] = []
    if any(k in lower for k in ("healing word", "bonus action")) and any(
        k in lower for k in ("fireball", "same turn", "and then cast", "magic action")
    ):
        extras.append("one spell with a spell slot per turn")
    if "exhaust" in lower:
        extras.append("Exhaustion condition d20 tests speed death level 6")
    if "inspiration" in lower:
        extras.append("Heroic Inspiration reroll one die")
    if "mastery" in lower or any(n in lower for n in _MASTERY_NAMES):
        extras.append("weapon mastery property PHB 2024")
    for weapon in list_weapons():
        label = str(weapon.get("label") or "").lower()
        if label and label in lower:
            extras.append(f"{label} weapon damage properties mastery {weapon.get('mastery') or ''}")
            break
    if extras:
        return f"{message.strip()}\n\n2024 rules: {'; '.join(extras)}"
    return message


def lookup_curated_rules(message: str, limit: int = 4) -> list[dict[str, str]]:
    """Return short curated snippets that should beat RAG for named rules."""
    lower = (message or "").lower()
    hits: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(key: str) -> None:
        if key in seen:
            return
        row = rules_glossary().get(key)
        if not isinstance(row, dict):
            return
        text = str(row.get("text") or "").strip()
        if not text:
            return
        seen.add(key)
        hits.append(
            {
                "title": str(row.get("title") or key),
                "page": str(row.get("page") or ""),
                "text": re.sub(r"\s+", " ", text).strip(),
            }
        )

    if any(k in lower for k in ("exhaust", "tired", "speed penalty")):
        add("exhaustion")
    if "inspiration" in lower:
        add("heroic_inspiration")
    if any(
        k in lower
        for k in (
            "spell slot per turn",
            "two leveled",
            "two levelled",
            "bonus action and",
            "healing word",
            "same turn",
        )
    ):
        add("one_spell_slot_per_turn")
    for name in _MASTERY_NAMES:
        if name in lower or f"{name} mastery" in lower:
            add(name)
    for weapon in list_weapons():
        label = str(weapon.get("label") or "")
        if not label:
            continue
        if normalize_spell_name(label) in normalize_spell_name(lower) or label.lower() in lower:
            mastery = str(weapon.get("mastery") or "").strip().lower()
            props = ", ".join(str(p) for p in (weapon.get("properties") or []))
            hits.append(
                {
                    "title": label,
                    "page": "215",
                    "text": (
                        f"{label}: {weapon.get('damage')} {weapon.get('damage_type')} "
                        f"({weapon.get('category')}"
                        f"{'; ' + props if props else ''}). "
                        f"Mastery: {mastery or 'none'}."
                    ),
                }
            )
            if mastery:
                add(mastery)
            break
        if len(hits) >= limit:
            break
    return hits[:limit]


def format_curated_context(hits: list[dict[str, str]]) -> str:
    if not hits:
        return ""
    lines = ["Curated 2024 rules:"]
    for i, hit in enumerate(hits, 1):
        page = f" p.{hit['page']}" if hit.get("page") else ""
        lines.append(f"[{i}] {hit['title']}{page}\n{hit['text']}")
    return "\n\n".join(lines)


def weapon_mastery_keywords() -> dict[str, str]:
    props = weapon_mastery_data().get("properties") or {}
    return {
        key: str((row or {}).get("summary") or "")
        for key, row in props.items()
        if isinstance(row, dict)
    }


def get_weapon_or_none(name: str) -> dict[str, Any] | None:
    return get_weapon(name)
