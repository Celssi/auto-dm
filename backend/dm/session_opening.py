"""Persist opening narration on a play session."""

from __future__ import annotations

from typing import Any

from backend.dm.prose_style import sanitize_narration_dashes
from backend.storage import save_session_messages


def attach_opening_to_session(*, session_id: str, opening: str) -> dict[str, Any]:
    cleaned = sanitize_narration_dashes(opening.strip())
    msg = {"role": "assistant", "content": cleaned}
    save_session_messages(session_id, [msg])
    return {"opening_scene": cleaned, "message": msg}
