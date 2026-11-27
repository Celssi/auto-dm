"""Session and play API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.dm.audit import read_audit_events, record_audit
from backend.dm.graph import run_dm_turn
from backend.dm.lonelog import format_mechanical
from backend.dm.opening_scene import begin_session
from backend.dm.oracles import ORACLE_TOOLS, run_oracle
from backend.dm.prose_style import sanitize_narration_dashes
from backend.dm.session_recap import get_or_refresh_recap
from backend.dm.session_world import get_or_refresh_world
from backend.dm.stream_turn import stream_dm_turn
from backend.dm.trace import audit_session_context
from backend.games.registry import get_game, resolve_game_id
from backend.session_locks import session_lock
from backend.storage import (
    append_session_log,
    create_session,
    delete_session,
    get_character,
    get_session,
    get_session_lonelog,
    list_sessions,
    patch_session,
    save_session_messages,
    update_session_extras,
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


class CombatActionBody(BaseModel):
    action: str
    target_id: str | None = None


class SessionPatchBody(BaseModel):
    name: str | None = None
    archived: bool | None = None


class PlaySettingsBody(BaseModel):
    story_mode: str | None = None
    card_source: str | None = None


@router.get("")
def list_all(include_archived: bool = False):
    return {"sessions": list_sessions(include_archived=include_archived)}


@router.get("/shortcuts")
def shortcuts(game_id: str | None = None, character_id: str | None = None):
    plugin = get_game(game_id)
    char = get_character(character_id) if character_id else None
    if char:
        from backend.games.registry import rebuild_character_dict

        char = rebuild_character_dict(char)
    return {"shortcuts": plugin.play.shortcuts_for_character(char or {})}


@router.get("/oracles")
def oracles():
    return {"oracles": [{"id": k, **v} for k, v in ORACLE_TOOLS.items()]}


@router.get("/{session_id}")
def get_one(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return {"session": sess}


@router.patch("/{session_id}")
def patch(session_id: str, body: SessionPatchBody):
    if body.name is None and body.archived is None:
        raise HTTPException(400, "Provide a name or archived flag")
    try:
        sess = patch_session(session_id, body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not sess:
        raise HTTPException(404, "Session not found")
    return {"session": sess}


def _normalize_play_settings(extras: dict | None) -> dict[str, str]:
    data = extras or {}
    story = str(data.get("story_mode") or "player").strip().lower()
    cards = str(data.get("card_source") or "virtual").strip().lower()
    if story not in ("player", "ai_narrator"):
        story = "player"
    if cards not in ("virtual", "physical"):
        cards = "virtual"
    return {"story_mode": story, "card_source": cards}


@router.get("/{session_id}/play-settings")
def read_play_settings(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return _normalize_play_settings(sess.get("extras"))


@router.patch("/{session_id}/play-settings")
def update_play_settings(session_id: str, body: PlaySettingsBody):
    if body.story_mode is None and body.card_source is None:
        raise HTTPException(400, "Provide story_mode or card_source")
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    extras = dict(sess.get("extras") or {})
    if body.story_mode is not None:
        mode = str(body.story_mode).strip().lower()
        if mode not in ("player", "ai_narrator"):
            raise HTTPException(400, "story_mode must be player or ai_narrator")
        extras["story_mode"] = mode
    if body.card_source is not None:
        source = str(body.card_source).strip().lower()
        if source not in ("virtual", "physical"):
            raise HTTPException(400, "card_source must be virtual or physical")
        extras["card_source"] = source
    update_session_extras(session_id, extras)
    return _normalize_play_settings(extras)


@router.get("/{session_id}/recap")
def recap(session_id: str, force: bool = False):
    try:
        return get_or_refresh_recap(session_id, force=force)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.get("/{session_id}/world")
def world(session_id: str, refresh: bool = False):
    try:
        return get_or_refresh_world(session_id, refresh=refresh)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.post("")
def create(body: SessionCreateBody):
    session_id = create_session(
        character_id=body.character_id,
        adventure_id=body.adventure_id,
        name=body.name,
        include_faerun=body.include_faerun,
    )
    return {"id": session_id, "session": get_session(session_id)}


@router.post("/{session_id}/begin")
def begin(session_id: str):
    try:
        return begin_session(session_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        from backend.dm.errors import http_provider_error

        raise http_provider_error(e) from e


def _execute_shortcut(session_id: str, body: ShortcutBody) -> dict:
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    char = get_character(sess["character_id"]) or {}
    params = {**char, **body.params}
    if resolve_game_id(char) == "brambletrek":
        from backend.games.brambletrek.play_handlers import get_session_combat_context

        ctx = get_session_combat_context(session_id)
        if ctx:
            params["combat_context"] = ctx
        # Honour the session's play settings (physical deck / story mode) like chat does.
        extras = sess.get("extras") or {}
        params.setdefault("card_source", extras.get("card_source", "virtual"))
        params.setdefault("story_mode", extras.get("story_mode", "player"))
    if body.pre_rolled is not None:
        if not body.pre_rolled:
            raise HTTPException(400, "pre_rolled must not be empty")
        if not all(1 <= v <= 20 for v in body.pre_rolled):
            raise HTTPException(400, "pre_rolled values must be between 1 and 20")
        params["pre_rolled"] = body.pre_rolled
    try:
        with audit_session_context(session_id):
            plugin = get_game(resolve_game_id(char))
            result = plugin.run_shortcut(body.shortcut_id, **params)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if isinstance(result.get("user_message"), str):
        result["user_message"] = sanitize_narration_dashes(result["user_message"])
    if isinstance(result.get("summary"), str):
        result["summary"] = sanitize_narration_dashes(result["summary"])
    # e.g. Brambletrek: stash journey draws so the Journey panel can Apply / Finish day.
    plugin.play.on_shortcut_result(session_id, {**char, "id": sess["character_id"]}, result)
    return result


@router.post("/{session_id}/chat")
def chat(session_id: str, body: ChatBody):
    try:
        result = run_dm_turn(session_id, body.message)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return result


@router.post("/{session_id}/chat/stream")
def chat_stream(session_id: str, body: ChatBody):
    if not get_session(session_id):
        raise HTTPException(404, "Session not found")
    return stream_dm_turn(session_id, body.message)


@router.post("/{session_id}/shortcut")
def shortcut(session_id: str, body: ShortcutBody):
    result = _execute_shortcut(session_id, body)
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


@router.post("/{session_id}/shortcut/stream")
def shortcut_stream(session_id: str, body: ShortcutBody):
    result = _execute_shortcut(session_id, body)
    if not body.narrate:
        raise HTTPException(400, "shortcut stream requires narrate=true")
    return stream_dm_turn(
        session_id,
        result.get("user_message", ""),
        precomputed_shortcut=result,
        prelude=[("shortcut", result)],
    )


@router.post("/{session_id}/oracle")
def run_session_oracle(session_id: str, body: OracleBody):
    with session_lock(session_id):
        sess = get_session(session_id)
        if not sess:
            raise HTTPException(404, "Session not found")
        try:
            result = run_oracle(body.oracle_id, likelihood_level=body.likelihood_level)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        summary = sanitize_narration_dashes(str(result.get("summary", "")))
        result["summary"] = summary
        messages = list(sess.get("messages") or [])
        messages.append({"role": "user", "content": f"[oracle: {body.oracle_id}]"})
        messages.append({"role": "assistant", "content": summary})
        save_session_messages(session_id, messages)
        append_session_log(session_id, format_mechanical(summary))
        record_audit(
            {
                "event": "oracle",
                "source": "oracle",
                "detail": {
                    "oracle_id": body.oracle_id,
                    "likelihood_level": body.likelihood_level,
                    "summary": summary,
                    "answer": result.get("answer"),
                    "inferred": False,
                },
            },
            session_id=session_id,
        )
        return result


@router.get("/{session_id}/audit")
def audit(session_id: str, limit: int = 200):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    events = read_audit_events(session_id, limit=limit)
    return {"events": events}


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


@router.get("/{session_id}/combat")
def get_combat(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    from backend.games.dnd5e.play_handlers import get_session_combat

    return {"combat_state": get_session_combat(session_id)}


@router.post("/{session_id}/combat")
def post_combat(session_id: str, body: CombatActionBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    from backend.games.dnd5e.play_handlers import session_combat_action

    return session_combat_action(session_id, action=body.action, target_id=body.target_id)
