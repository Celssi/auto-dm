"""D&D 5e play session handlers (combat API)."""

from __future__ import annotations

from backend.dm.encounters import combat_state_view, load_combat_state
from backend.games.dnd5e.dm.combat_manager import combat_action
from backend.session_locks import session_lock
from backend.storage import get_character, get_session, patch_character


def get_session_combat(session_id: str) -> dict:
    return combat_state_view(load_combat_state(session_id))


def session_combat_action(
    session_id: str,
    *,
    action: str,
    target_id: str | None = None,
) -> dict:
    with session_lock(session_id):
        sess = get_session(session_id)
        if not sess:
            return {"error": "session_not_found"}
        char_row = get_character(sess["character_id"])
        if not char_row:
            return {"error": "character_not_found"}
        char_dict = dict(char_row)
        state, updated_char, events, meta = combat_action(
            session_id,
            action,
            char_dict,
            target_id=target_id,
        )
        if updated_char.get("hp") != char_dict.get("hp"):
            updated_char = patch_character(
                sess["character_id"],
                {"hp": updated_char.get("hp"), "ac": updated_char.get("ac")},
            )
    out = {
        "combat_state": meta.get("combat_state") or combat_state_view(state),
        "events": events,
        "character": updated_char,
    }
    if meta.get("error"):
        out["error"] = meta["error"]
    return out
