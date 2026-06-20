"""Session and play API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.dm.actions import SHORTCUTS, run_shortcut
from backend.dm.graph import run_dm_turn
from backend.dm.lonelog import format_mechanical
from backend.dm.opening_scene import begin_session
from backend.dm.oracles import ORACLE_TOOLS, run_oracle
from backend.settings_store import load_settings
from backend.storage import (
    append_session_log,
    create_session,
    delete_session,
    get_character,
    get_session,
    get_session_lonelog,
    list_sessions,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreateBody(BaseModel):
    character_id: str
    adventure_id: str
    name: str = ""
    include_faerun: bool = False


class ChatBody(BaseModel):
    message: str


class ShortcutBody(BaseModel):
    shortcut_id: str
    params: dict = {}
    pre_rolled: list[int] | None = None
    narrate: bool = False


class OracleBody(BaseModel):
    oracle_id: str
    likelihood_level: str = "fifty_fifty"


@router.get("")
def list_all():
    return {"sessions": list_sessions()}


@router.get("/shortcuts")
def shortcuts():
    return {"shortcuts": SHORTCUTS}


@router.get("/oracles")
def oracles():
    return {"oracles": [{"id": k, **v} for k, v in ORACLE_TOOLS.items()]}


@router.get("/{session_id}")
def get_one(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return {"session": sess}


@router.post("")
def create(body: SessionCreateBody):
    prefs = load_settings()
    session_id = create_session(
        character_id=body.character_id,
        adventure_id=body.adventure_id,
        name=body.name,
        include_faerun=body.include_faerun or prefs.get("include_faerun", False),
    )
    return {"id": session_id, "session": get_session(session_id)}


@router.post("/{session_id}/begin")
def begin(session_id: str):
    try:
        return begin_session(session_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{session_id}/chat")
def chat(session_id: str, body: ChatBody):
    try:
        result = run_dm_turn(session_id, body.message)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return result


@router.post("/{session_id}/shortcut")
def shortcut(session_id: str, body: ShortcutBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    char = get_character(sess["character_id"]) or {}
    params = {**char, **body.params}
    if body.pre_rolled is not None:
        if not body.pre_rolled:
            raise HTTPException(400, "pre_rolled must not be empty")
        if not all(1 <= v <= 20 for v in body.pre_rolled):
            raise HTTPException(400, "pre_rolled values must be between 1 and 20")
        params["pre_rolled"] = body.pre_rolled
    try:
        result = run_shortcut(body.shortcut_id, **params)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not body.narrate:
        return result
    try:
        dm_result = run_dm_turn(
            session_id,
            result.get("user_message", ""),
            precomputed_shortcut=result,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    dm_result["shortcut"] = result
    return dm_result


@router.post("/{session_id}/oracle")
def run_session_oracle(session_id: str, body: OracleBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        result = run_oracle(body.oracle_id, likelihood_level=body.likelihood_level)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    append_session_log(session_id, format_mechanical(result.get("summary", "")))
    return result


@router.get("/{session_id}/lonelog")
def lonelog(session_id: str):
    content = get_session_lonelog(session_id)
    lines = content.splitlines()[-80:]
    return {"lines": lines}


@router.delete("/{session_id}")
def remove(session_id: str):
    if not delete_session(session_id):
        raise HTTPException(404, "Session not found")
    return {"ok": True}
