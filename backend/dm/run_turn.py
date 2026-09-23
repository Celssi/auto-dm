"""Run a single DM turn through the per-game agent pipeline."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables.config import RunnableConfig

from backend.config import LANGSMITH_ENABLED
from backend.dm.encounters import combat_state_view, load_combat_state
from backend.dm.graph_factory import get_dm_graph
from backend.dm.lonelog import format_mechanical
from backend.dm.state import DMState
from backend.dm.trace import dm_turn_trace
from backend.games.registry import get_game, resolve_game_id
from backend.llm import ChatProvider
from backend.settings_store import load_settings
from backend.storage import (
    append_session_log,
    get_adventure,
    get_character,
    get_session,
    save_character,
    save_session_messages,
)


def _graph_run_config(session_id: str, user_message: str) -> RunnableConfig:
    return RunnableConfig(
        run_name="dm_turn",
        tags=["auto-dm", "dm_turn"],
        metadata={
            "session_id": session_id,
            "user_message": user_message[:500],
        },
    )


def run_dm_turn(
    session_id: str,
    user_message: str,
    *,
    chat_provider: ChatProvider = "claude",
    precomputed_shortcut: dict | None = None,
) -> dict[str, Any]:
    _ = chat_provider
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")
    char = get_character(session["character_id"]) or {}
    game_id = resolve_game_id(char)
    plugin = get_game(game_id)
    adventure = get_adventure(session["adventure_id"]) or {}
    messages = session.get("messages") or []
    messages.append({"role": "user", "content": user_message})
    character_id = session["character_id"]

    pre_turn_result = plugin.play.pre_turn(
        session_id,
        user_message,
        char,
        messages,
        adventure,
        character_id,
    )
    if isinstance(pre_turn_result, dict) and pre_turn_result.get("response") is not None:
        return pre_turn_result

    pre_combat_events: list[str] = []
    if isinstance(pre_turn_result, dict):
        char = pre_turn_result.get("character") or char
        pre_combat_events = list(pre_turn_result.get("pre_combat_events") or [])

    adventure = get_adventure(session["adventure_id"]) or {}
    prefs = load_settings()
    state: DMState = {
        "session_id": session_id,
        "user_message": user_message,
        "character": char,
        "adventure": adventure,
        "include_faerun": session.get("include_faerun", False)
        or prefs.get("include_faerun", False),
        "messages": messages[:-1],
        "combat_events": pre_combat_events,
    }
    if precomputed_shortcut:
        state["precomputed_shortcut"] = precomputed_shortcut

    run_config = _graph_run_config(session_id, user_message) if LANGSMITH_ENABLED else None
    with dm_turn_trace(session_id, user_message):
        result = get_dm_graph(game_id).invoke(state, config=run_config or {})
    response = result.get("response", "")
    post_events = list(result.get("combat_events") or [])
    all_combat_lines = pre_combat_events + post_events
    if all_combat_lines:
        combat_block = "\n\n".join(all_combat_lines)
        response = f"{combat_block}\n\n{response}" if response.strip() else combat_block

    sources = result.get("rules_sources") or []
    updated_char = result.get("character") or char
    if updated_char != char:
        save_character(character_id, updated_char)

    messages.append({"role": "assistant", "content": response})
    save_session_messages(session_id, messages)
    for line in pre_combat_events + post_events:
        append_session_log(session_id, format_mechanical(line))

    combat_view = combat_state_view(load_combat_state(session_id))

    return {
        "response": response,
        "sources": sources,
        "character": updated_char,
        "lonelog_lines": result.get("lonelog_lines") or [],
        "adventure_complete": bool(result.get("adventure_complete")),
        "next_adventure": result.get("next_adventure"),
        "player_progress": result.get("player_progress") or {},
        "combat_state": combat_view,
    }


if LANGSMITH_ENABLED:
    from langsmith import traceable

    run_dm_turn = traceable(name="run_dm_turn", run_type="chain")(run_dm_turn)
