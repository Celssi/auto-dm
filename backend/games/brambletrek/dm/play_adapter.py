"""Brambletrek play adapter."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.actions import shortcuts_list_for_character
from backend.games.brambletrek.dm.agents.nodes import detect_brambletrek_shortcut
from backend.games.brambletrek.dm.bootstrap import (
    bootstrap_brambletrek_campaign,
    generate_brambletrek_opening,
)
from backend.games.brambletrek.dm.pipeline import build_brambletrek_graph
from backend.games.play_adapter import GamePlayAdapter


def _shortcut_extras(session: dict) -> dict[str, Any]:
    extras = session.get("extras") or {}
    return {
        "card_source": extras.get("card_source", "virtual"),
        "story_mode": extras.get("story_mode", "player"),
    }


def _on_shortcut_result(session_id: str, char: dict, result: dict) -> None:
    if result.get("journey_cards"):
        from backend.games.brambletrek.play_handlers import stash_pending_journey

        stash_pending_journey(
            session_id,
            str(char.get("id") or ""),
            result,
            result.get("journey_shortcut_id") or "journey_day",
        )


def _pre_turn(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {}


def _shortcuts_for_character(char: dict) -> list[dict[str, str]]:
    active = str(char.get("active_adventure") or "")
    return shortcuts_list_for_character(active_adventure=active)


BRAMBLETREK_PLAY_ADAPTER = GamePlayAdapter(
    rag_direct_tasks=frozenset({"rag_direct"}),
    supports_level_up=False,
    supports_campaign_plan=False,
    skip_chronicler=True,
    skip_journal_keeper=True,
    detect_shortcut=detect_brambletrek_shortcut,
    shortcut_extras=_shortcut_extras,
    on_shortcut_result=_on_shortcut_result,
    pre_turn=_pre_turn,
    shortcuts_for_character=_shortcuts_for_character,
    bootstrap_campaign=bootstrap_brambletrek_campaign,
    generate_opening=generate_brambletrek_opening,
    build_graph=build_brambletrek_graph,
)
