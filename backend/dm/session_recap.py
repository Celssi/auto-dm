"""Player-facing 'Previously on…' recap, cached per session."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.dm.lonelog import extract_narrative_snippets
from backend.dm.prose_style import sanitize_narration_dashes
from backend.games.registry import resolve_game_id
from backend.llm import get_langchain_chat_llm, invoke_chat_llm, message_text
from backend.storage import (
    get_adventure,
    get_adventure_summary,
    get_character,
    get_session,
    get_session_recap_cache,
    save_session_recap_cache,
)

RECAP_MAX_CHARS = 900
FALLBACK_ASSISTANT_TURNS = 3
MESSAGE_SNIPPET = 700
LOG_SNIPPETS = 8


def session_message_count(session: dict[str, Any] | None) -> int:
    if not session:
        return 0
    return len(session.get("messages") or [])


def fallback_recap(*, messages: list[dict[str, Any]] | None = None, lonelog: str = "") -> str:
    """Build a short recap from existing prose when the LLM is unavailable."""
    parts: list[str] = []
    assistant = [
        str(m.get("content") or "").strip()
        for m in (messages or [])
        if m.get("role") == "assistant" and str(m.get("content") or "").strip()
    ]
    for text in assistant[-FALLBACK_ASSISTANT_TURNS:]:
        clipped = " ".join(text.split())
        if len(clipped) > MESSAGE_SNIPPET:
            clipped = clipped[:MESSAGE_SNIPPET].rsplit(" ", 1)[0] + "…"
        parts.append(clipped)
    if not parts:
        snippets = extract_narrative_snippets(lonelog)
        for snippet in snippets[-LOG_SNIPPETS:]:
            clipped = " ".join(snippet.split())
            if clipped:
                parts.append(clipped)
    body = " ".join(parts).strip()
    if not body:
        return ""
    if len(body) > RECAP_MAX_CHARS:
        body = body[:RECAP_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return sanitize_narration_dashes(body)


def generate_recap(
    *,
    messages: list[dict[str, Any]] | None = None,
    lonelog: str = "",
    adventure_summary: str = "",
    character_name: str = "",
    game_id: str = "dnd5e",
) -> str:
    """Ask Claude for a short player-facing recap of play so far."""
    transcript_bits: list[str] = []
    for msg in (messages or [])[-16:]:
        role = "Player" if msg.get("role") == "user" else "DM"
        content = " ".join(str(msg.get("content") or "").split())
        if not content:
            continue
        transcript_bits.append(f"{role}: {content[:500]}")
    snippets = extract_narrative_snippets(lonelog)
    log_text = "\n".join(f"- {s}" for s in snippets[-LOG_SNIPPETS:])
    game_id_resolved = resolve_game_id({"game_id": game_id})
    game_label = "Brambletrek" if game_id_resolved == "brambletrek" else "D&D 5e"
    hero = character_name.strip() or "the hero"
    prompt = f"""Write a short 'Previously on…' recap for a {game_label} solo player.

Rules:
- 2-4 sentences, or two short paragraphs at most
- Recap only events that already happened
- Do not spoil future plot or unused secrets
- Speak to the player in second person when natural, or name {hero}
- Do not use em dashes or en dashes; use commas, periods, or plain hyphens for ranges
- No heading, no bullet list, no title

Adventure canon (may be empty):
{adventure_summary[:2500] or "(none)"}

Recent log:
{log_text or "(none)"}

Recent transcript:
{chr(10).join(transcript_bits) or "(none)"}
"""
    llm = get_langchain_chat_llm("claude", effort="medium")
    response = invoke_chat_llm(
        llm,
        [
            SystemMessage(
                content="Write a spoiler-safe recap of story so far for a returning solo player."
            ),
            HumanMessage(content=prompt),
        ],
        agent="session_recap",
        provider="claude",
    )
    return sanitize_narration_dashes(message_text(response).strip())


def _adventure_summary_for_session(session: dict[str, Any]) -> str:
    adv_id = str(session.get("adventure_id") or "").strip()
    if not adv_id:
        return ""
    summary = get_adventure_summary(adv_id).strip()
    if summary:
        return summary
    return str((get_adventure(adv_id) or {}).get("summary") or "")


def get_or_refresh_recap(session_id: str, *, force: bool = False) -> dict[str, Any]:
    """Return a cached recap, regenerating when the session has new turns."""
    session = get_session(session_id)
    if not session:
        raise ValueError("Session not found")
    count = session_message_count(session)
    empty = {"text": "", "message_count": count, "stale": False}
    if count <= 0:
        return empty

    cached = get_session_recap_cache(session_id) or {}
    cached_text = str(cached.get("text") or "").strip()
    cached_count = cached.get("message_count")
    if not force and cached_text and cached_count == count:
        return {"text": cached_text, "message_count": count, "stale": False}

    character = get_character(str(session.get("character_id") or "")) or {}
    try:
        text = generate_recap(
            messages=session.get("messages") or [],
            lonelog=str(session.get("lonelog") or ""),
            adventure_summary=_adventure_summary_for_session(session),
            character_name=str(character.get("name") or ""),
            game_id=resolve_game_id(character),
        )
    except Exception:
        text = fallback_recap(
            messages=session.get("messages") or [],
            lonelog=str(session.get("lonelog") or ""),
        )
    text = sanitize_narration_dashes(text.strip())
    payload = {"text": text, "message_count": count}
    save_session_recap_cache(session_id, payload)
    return {**payload, "stale": False}
