"""Shared DM graph state and helpers."""

from __future__ import annotations

from typing import TypedDict

from backend.games.registry import get_game, resolve_game_id


class DMState(TypedDict, total=False):
    session_id: str
    user_message: str
    character: dict
    adventure: dict
    include_faerun: bool
    messages: list[dict]
    in_combat: bool
    needs_rules: bool
    rules_context: str
    rules_sources: list[dict]
    mechanics_summary: str
    combat_context: str
    shortcut_result: dict
    narrative: str
    character_updates: dict
    response: str
    sources: list[dict]
    lonelog_lines: list[str]
    scribe_log_entry: str
    continuity_issues: list[str]
    narrative_context: dict
    resource_log: list[str]
    story_brief: str
    story_progress: dict
    adventure_complete: bool
    next_adventure: dict | None
    player_progress: dict
    combat_state: dict
    combat_events: list[str]
    precomputed_shortcut: dict
    journal_updates: dict


def game_plugin(char_dict: dict | None = None):
    return get_game(resolve_game_id(char_dict))


def char_from_dict(char_dict: dict):
    return game_plugin(char_dict).character_from_dict(char_dict)


def factions_for(include_faerun: bool, game_id: str | None = None) -> list[str]:
    if include_faerun:
        return get_game(game_id).get_all_factions()
    return ["player", "dm", "monsters"]
