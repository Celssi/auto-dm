"""Persist opening narration on a play session."""

from __future__ import annotations

from typing import Any

from backend.storage import save_session_messages


def attach_opening_to_session(*, session_id: str, opening: str) -> dict[str, Any]:
    msg = {"role": "assistant", "content": opening.strip()}
    save_session_messages(session_id, [msg])
    return {"opening_scene": opening.strip(), "message": msg}
