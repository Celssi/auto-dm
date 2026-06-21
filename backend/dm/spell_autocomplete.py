"""Fuzzy spell name detection and cast confirmation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from backend.characters.entity import Dnd5eCharacter, character_from_dict, character_to_dict
from backend.characters.spell_resources import (
    _subclass_always_prepared,
    normalize_spell_name,
)
from backend.dm.lonelog import format_mechanical
from backend.dm.resource_keeper import apply_cast_spell_shortcut

_CAST_PATTERNS = (
    re.compile(r"^/cast\s+(.+)$", re.IGNORECASE),
    re.compile(r"^cast\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bi\s+cast\s+(.+?)(?:\s+at\b|\s+on\b|\s+against\b|[.!,]|$)", re.IGNORECASE),
    re.compile(r"\bcasting\s+(.+?)(?:\s+at\b|\s+on\b|\s+against\b|[.!,]|$)", re.IGNORECASE),
)

_CONFIRM_WORDS = frozenset(
    {"yes", "y", "yeah", "yep", "confirm", "confirmed", "do it", "cast it", "jep", "kyllä", "kylla"}
)
_CANCEL_WORDS = frozenset(
    {
        "no",
        "n",
        "nope",
        "cancel",
        "nevermind",
        "never mind",
        "ei",
        "peru",
        "peruuta",
        "cancel spell",
    }
)


@dataclass(frozen=True)
class SpellQueryResolution:
    status: Literal["exact", "fuzzy", "unknown"]
    spell_name: str = ""
    requested: str = ""
    score: float = 0.0


def list_character_spells(char: Dnd5eCharacter) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for group in (
        char.cantrips,
        char.prepared_spells,
        char.known_spells,
        _subclass_always_prepared(char),
    ):
        for name in group:
            key = normalize_spell_name(str(name))
            if key and key not in seen:
                seen.add(key)
                names.append(str(name).strip())
    return names


def _similarity(a: str, b: str) -> float:
    na, nb = normalize_spell_name(a), normalize_spell_name(b)
    if not na or not nb:
        return 0.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    prefix = 0
    for x, y in zip(na, nb, strict=False):
        if x != y:
            break
        prefix += 1
    if prefix >= 4:
        ratio = max(ratio, min(0.95, 0.52 + prefix * 0.05))
    return ratio


def extract_cast_query(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    for pattern in _CAST_PATTERNS:
        match = pattern.search(text)
        if match:
            query = match.group(1).strip()
            if query:
                return query
    return None


def resolve_spell_query(char: Dnd5eCharacter, query: str) -> SpellQueryResolution:
    requested = query.strip()
    normalized = normalize_spell_name(requested)
    if not normalized:
        return SpellQueryResolution(status="unknown", requested=requested)

    available = list_character_spells(char)
    if not available:
        return SpellQueryResolution(status="unknown", requested=requested)

    for name in available:
        if normalize_spell_name(name) == normalized:
            return SpellQueryResolution(
                status="exact", spell_name=name, requested=requested, score=1.0
            )

    ranked = sorted(
        ((name, _similarity(requested, name)) for name in available), key=lambda x: -x[1]
    )
    best_name, best_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    if best_score >= 0.62 and best_score - runner_up >= 0.05:
        return SpellQueryResolution(
            status="fuzzy",
            spell_name=best_name,
            requested=requested,
            score=best_score,
        )
    return SpellQueryResolution(status="unknown", requested=requested)


def is_spell_confirmation(message: str) -> bool:
    lower = (message or "").strip().lower()
    if lower in _CONFIRM_WORDS:
        return True
    if lower.startswith("yes "):
        return True
    return False


def is_spell_cancel(message: str) -> bool:
    lower = (message or "").strip().lower()
    return lower in _CANCEL_WORDS


def confirmation_message(resolution: SpellQueryResolution) -> str:
    return (
        f'You wrote **"{resolution.requested}"**. Did you mean **{resolution.spell_name}**?\n\n'
        f"Reply **yes** or tap **Cast {resolution.spell_name}** "
        "to spend the slot deterministically, "
        f"or **no** to continue without the cast shortcut."
    )


def execute_confirmed_cast(char: Dnd5eCharacter, spell_name: str) -> tuple[dict, str, list[str]]:
    char_dict = character_to_dict(char)
    entity, logs = apply_cast_spell_shortcut(
        char_dict, spell_name, audit_source="spell_autocomplete"
    )
    updated = dict(char_dict)
    updated.update(entity)
    char = character_from_dict(updated)
    summary = logs[0] if logs else f"Cast {spell_name}."
    response = f"**Cast {spell_name}**\n\n{summary}"
    lonelog = [format_mechanical(summary)]
    return character_to_dict(char), response, lonelog
