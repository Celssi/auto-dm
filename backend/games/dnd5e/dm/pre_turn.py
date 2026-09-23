"""D&D pre-turn hooks: spell autocomplete and combat initialization."""

from __future__ import annotations

from typing import Any

from backend.dm.encounters import load_combat_state
from backend.dm.state import char_from_dict
from backend.games.dnd5e.characters.spell_resources import is_spell_available
from backend.games.dnd5e.dm.combat_manager import (
    run_enemy_turns_until_player,
    try_start_planned_encounter,
)
from backend.games.dnd5e.dm.spell_autocomplete import (
    confirmation_message,
    execute_confirmed_cast,
    extract_cast_query,
    is_spell_cancel,
    is_spell_confirmation,
    list_character_spells,
    resolve_spell_query,
)
from backend.storage import (
    append_session_log,
    get_character,
    get_session,
    save_character,
    save_session_messages,
    update_session,
)


def _finish_early_turn(
    session_id: str,
    messages: list[dict],
    *,
    response: str,
    character: dict,
    character_id: str,
    spell_confirmation: dict | None = None,
    lonelog_lines: list[str] | None = None,
    clear_pending: bool = False,
    persist_character: bool = False,
) -> dict[str, Any]:
    if clear_pending:
        update_session(session_id, {"pending_spell_cast": None})
    messages.append({"role": "assistant", "content": response})
    save_session_messages(session_id, messages)
    for line in lonelog_lines or []:
        append_session_log(session_id, line)
    if persist_character:
        save_character(character_id, character)
    out: dict[str, Any] = {
        "response": response,
        "sources": [],
        "character": character,
        "lonelog_lines": lonelog_lines or [],
    }
    if spell_confirmation:
        out["spell_confirmation"] = spell_confirmation
    return out


def handle_spell_autocomplete(
    session_id: str,
    user_message: str,
    char: dict,
    messages: list[dict],
) -> dict[str, Any] | None:
    character_id = (get_session(session_id) or {}).get("character_id", "")
    session = get_session(session_id) or {}
    pending = session.get("pending_spell_cast")

    if pending and isinstance(pending, dict):
        spell_name = str(pending.get("spell_name") or pending.get("suggested") or "").strip()
        if is_spell_cancel(user_message):
            return _finish_early_turn(
                session_id,
                messages,
                response=(
                    f"Okay, not casting **{spell_name or 'that spell'}**. What do you do instead?"
                ),
                character=char,
                character_id=character_id,
                clear_pending=True,
            )
        if is_spell_confirmation(user_message) and spell_name:
            updated_char, response, lonelog = execute_confirmed_cast(
                char_from_dict(char),
                spell_name,
            )
            return _finish_early_turn(
                session_id,
                messages,
                response=response,
                character=updated_char,
                character_id=character_id,
                lonelog_lines=lonelog,
                clear_pending=True,
                persist_character=True,
            )

    query = extract_cast_query(user_message)
    if not query:
        return None

    resolution = resolve_spell_query(char_from_dict(char), query)
    if resolution.status == "exact":
        if pending:
            update_session(session_id, {"pending_spell_cast": None})
        return None

    if resolution.status == "fuzzy":
        update_session(
            session_id,
            {
                "pending_spell_cast": {
                    "requested": resolution.requested,
                    "suggested": resolution.spell_name,
                    "spell_name": resolution.spell_name,
                }
            },
        )
        return _finish_early_turn(
            session_id,
            messages,
            response=confirmation_message(resolution),
            character=char,
            character_id=character_id,
            spell_confirmation={
                "requested": resolution.requested,
                "suggested": resolution.spell_name,
                "spell_name": resolution.spell_name,
            },
        )

    if resolution.status == "unknown" and query:
        available = list_character_spells(char_from_dict(char))
        if available and not is_spell_available(char_from_dict(char), query):
            hint = ", ".join(available[:8])
            return _finish_early_turn(
                session_id,
                messages,
                response=(
                    f'I could not match **"{query}"** to a spell on your sheet. '
                    f"Prepared/known: {hint}{'…' if len(available) > 8 else ''}."
                ),
                character=char,
                character_id=character_id,
                clear_pending=True,
            )
    return None


def run_combat_pre_turn(
    session_id: str,
    user_message: str,
    char: dict,
    adventure_id: str,
    character_id: str,
    messages: list[dict],
) -> tuple[dict, list[str]]:
    """Initialize combat and run enemy turns before the graph. Returns (char, pre_combat_events)."""
    pre_combat_events: list[str] = []
    combat_before = load_combat_state(session_id)
    if adventure_id and not combat_before:
        try_start_planned_encounter(
            session_id,
            adventure_id,
            char,
            user_message=user_message,
            messages=messages,
        )

    combat_after_start = load_combat_state(session_id)
    combat_started_this_turn = bool(combat_after_start and not combat_before)
    if combat_after_start and not combat_started_this_turn:
        _, char, pre_combat_events = run_enemy_turns_until_player(session_id, char)
    elif combat_started_this_turn:
        _, char, _ = run_enemy_turns_until_player(session_id, char, resolve_enemies=False)
    if char != get_character(character_id):
        save_character(character_id, char)
    return char, pre_combat_events
