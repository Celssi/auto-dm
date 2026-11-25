"""Per-game play session adapter and agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class GamePlayAdapter:
    """Behavioral hooks for play sessions, routes, and DM graph selection."""

    rag_direct_tasks: frozenset[str]
    supports_level_up: bool
    supports_campaign_plan: bool
    skip_chronicler: bool
    skip_journal_keeper: bool
    detect_shortcut: Callable[[str, dict | None], str | None]
    shortcut_extras: Callable[[dict], dict[str, Any]]
    on_shortcut_result: Callable[[str, dict, dict], None]
    pre_turn: Callable[..., dict[str, Any] | None]
    shortcuts_for_character: Callable[[dict], list[dict[str, str]]]
    bootstrap_campaign: Callable[..., dict[str, Any]]
    generate_opening: Callable[..., str]
    build_graph: Callable[[], Any]
    # D&D-only story director (campaign beats) runs after each turn unless skipped.
    skip_story_director: bool = False
    # Keep HP/slots/etc. from the live sheet when rebuilding the character.
    preserve_live_resources: bool = False
