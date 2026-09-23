"""Brambletrek character build helpers."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.characters.entity import (
    BrambletrekCharacter,
    character_from_dict,
    format_summary,
    label_for_band,
)


def rebuild_character(char: BrambletrekCharacter, **_kwargs) -> BrambletrekCharacter:
    char.clamp_stats()
    return char


def finalize_new_character(char: BrambletrekCharacter) -> BrambletrekCharacter:
    char.clamp_stats()
    return char


def character_creation_summary(char: BrambletrekCharacter) -> dict[str, Any]:
    return {
        "summary_line": format_summary(char),
        "health": char.health,
        "morale": char.morale,
        "supplies": char.supplies,
        "journey_day": char.journey_day,
        "legacy": char.legacy,
        "reason": label_for_band("reasons", char.reason_band) if char.reason_band else "",
        "background": label_for_band("backgrounds", char.background_band)
        if char.background_band
        else "",
        "trinket": label_for_band("trinkets", char.trinket_band) if char.trinket_band else "",
        "active_adventure": char.active_adventure,
    }


def character_from_dict_rebuild(data: dict | None) -> BrambletrekCharacter:
    return rebuild_character(character_from_dict(data))
