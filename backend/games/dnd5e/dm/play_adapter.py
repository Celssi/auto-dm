"""D&D 5e play adapter."""

from __future__ import annotations

from typing import Any

from backend.games.dnd5e.actions import SHORTCUTS
from backend.games.dnd5e.dm.agents.nodes import detect_dnd_shortcut
from backend.games.dnd5e.dm.pipeline import build_dnd_graph
from backend.games.dnd5e.dm.pre_turn import handle_spell_autocomplete, run_combat_pre_turn
from backend.games.play_adapter import GamePlayAdapter


def _shortcut_extras(_session: dict) -> dict[str, Any]:
    return {}


def _on_shortcut_result(_session_id: str, _char: dict, _result: dict) -> None:
    return None


def _pre_turn(
    session_id: str,
    user_message: str,
    char: dict,
    messages: list[dict],
    adventure: dict,
    character_id: str,
) -> dict[str, Any] | None:
    early = handle_spell_autocomplete(session_id, user_message, char, messages)
    if early is not None:
        return early
    adv_id = adventure.get("id", "")
    char, pre_events = run_combat_pre_turn(
        session_id, user_message, char, adv_id, character_id, messages[:-1]
    )
    return {"character": char, "pre_combat_events": pre_events}


def _bootstrap_campaign(**kwargs: Any) -> dict[str, Any]:
    from backend.games.dnd5e.dm.bootstrap import bootstrap_dnd_campaign

    return bootstrap_dnd_campaign(**kwargs)


def _generate_opening(char: dict, adv: dict | None = None) -> str:
    from backend.games.dnd5e.dm.bootstrap import generate_dnd_opening

    return generate_dnd_opening(char, adv)


DND_PLAY_ADAPTER = GamePlayAdapter(
    rag_direct_tasks=frozenset({"rules_help"}),
    supports_level_up=True,
    supports_campaign_plan=True,
    skip_chronicler=False,
    skip_journal_keeper=False,
    detect_shortcut=detect_dnd_shortcut,
    shortcut_extras=_shortcut_extras,
    on_shortcut_result=_on_shortcut_result,
    pre_turn=_pre_turn,
    shortcuts_for_character=lambda _char: list(SHORTCUTS),
    bootstrap_campaign=_bootstrap_campaign,
    generate_opening=_generate_opening,
    build_graph=build_dnd_graph,
)
