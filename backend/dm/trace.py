"""DM agent pipeline tracing — always logs to console + JSONL per session."""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR

DEBUG_DIR = DATA_DIR / "debug" / "dm"
MAX_TEXT = 120_000
CONSOLE_PREVIEW = 500

_turn_ctx: ContextVar[dict[str, str] | None] = ContextVar("dm_turn", default=None)
_logger = logging.getLogger("auto_dm.dm")


def _ensure_logger() -> None:
    if _logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def _preview(text: Any, limit: int = CONSOLE_PREVIEW) -> str:
    s = str(text or "").replace("\n", " ").strip()
    if len(s) <= limit:
        return s
    return s[:limit] + f"… (+{len(s) - limit} chars)"


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f"\n… [{len(value) - MAX_TEXT} chars truncated]"
    if isinstance(value, list) and len(value) > 50:
        return value[:50] + [f"… [{len(value) - 50} more items]"]
    return value


def _summarize_state(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    summary: dict[str, Any] = {}
    for key, value in data.items():
        if key == "character" and isinstance(value, dict):
            summary[key] = {
                "name": value.get("name"),
                "level": value.get("level"),
                "class_name": value.get("class_name"),
                "hp": value.get("hp"),
            }
        elif key == "adventure" and isinstance(value, dict):
            summary[key] = {
                "id": value.get("id"),
                "name": value.get("name"),
                "mode": value.get("mode"),
            }
        elif key == "messages" and isinstance(value, list):
            summary[key] = [
                {"role": m.get("role"), "preview": (m.get("content") or "")[:120]}
                for m in value[-5:]
            ]
        else:
            summary[key] = _truncate(value)
    return summary


def _state_one_liner(state: dict[str, Any] | None) -> str:
    if not state:
        return "(empty)"
    parts: list[str] = []
    for key, value in state.items():
        if key == "character" and isinstance(value, dict):
            parts.append(f"char={value.get('name', '?')} lv{value.get('level', '?')}")
        elif key == "messages":
            parts.append(f"history={len(value or [])} msgs")
        elif key in ("rules_context", "combat_context", "narrative", "response") and value:
            parts.append(f"{key}={len(str(value))} chars")
        elif isinstance(value, (bool, int, float)) or value in (None, "", [], {}):
            if value not in (None, "", [], {}, False):
                parts.append(f"{key}={value}")
        elif isinstance(value, str):
            parts.append(f"{key}={_preview(value, 80)}")
        elif isinstance(value, dict) and value:
            parts.append(f"{key}={len(value)} fields")
    return ", ".join(parts) if parts else "(no changes)"


def messages_to_dict(messages: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = getattr(msg, "type", None) or msg.__class__.__name__.replace("Message", "").lower()
        content = getattr(msg, "content", str(msg))
        out.append({"role": role, "content": _truncate(content)})
    return out


def _print_console(event: dict[str, Any]) -> None:
    _ensure_logger()
    agent = event.get("agent", "?")
    phase = event.get("phase", "?")

    if agent == "pipeline":
        if phase == "turn_start":
            turn = (event.get("turn_id") or "?")[:8]
            _logger.info("[DM] ── turn %s ── %s", turn, _preview(event.get("user_message"), 200))
        elif phase == "turn_end":
            _logger.info("[DM] ── turn end ──")
        return

    if phase in ("enter", "exit"):
        arrow = "→" if phase == "enter" else "←"
        state = event.get("state")
        _logger.info("[DM] %s %s %s  %s", agent, arrow, phase, _state_one_liner(state))
        return

    if phase == "request":
        model = event.get("model") or "?"
        _logger.info("[DM] %s · Claude → request (%s)", agent, model)
        for msg in event.get("messages") or []:
            role = msg.get("role", "?")
            _logger.info("[DM]   [%s] %s", role, _preview(msg.get("content")))
        return

    if phase == "response":
        model = event.get("model") or "?"
        text = event.get("response") or ""
        _logger.info("[DM] %s · Claude ← response (%s, %d chars)", agent, model, len(str(text)))
        _logger.info("[DM]   %s", _preview(text))
        return

    if phase == "rag_query":
        _logger.info(
            "[DM] %s · RAG  query=%s  sources=%s  answer=%s",
            agent,
            _preview(event.get("query"), 120),
            event.get("source_count", 0),
            "yes" if event.get("has_answer") else "no",
        )
        return

    # Fallback for other events
    extras = {k: v for k, v in event.items() if k not in ("ts", "agent", "phase", "session_id", "turn_id")}
    if extras:
        _logger.info("[DM] %s · %s  %s", agent, phase, _preview(extras, 300))


def _write(event: dict[str, Any]) -> None:
    ctx = _turn_ctx.get()
    if ctx:
        event.setdefault("session_id", ctx["session_id"])
        event.setdefault("turn_id", ctx["turn_id"])
    event["ts"] = datetime.now(UTC).isoformat()
    _print_console(event)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    session_id = event.get("session_id") or "global"
    path = DEBUG_DIR / f"{session_id}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


@contextmanager
def dm_turn_trace(session_id: str, user_message: str):
    turn_id = uuid.uuid4().hex[:12]
    token = _turn_ctx.set({"session_id": session_id, "turn_id": turn_id})
    log_agent("pipeline", "turn_start", user_message=user_message)
    try:
        yield turn_id
    finally:
        log_agent("pipeline", "turn_end")
        _turn_ctx.reset(token)


def log_agent(agent: str, phase: str, **data: Any) -> None:
    payload = {k: _truncate(v) for k, v in data.items()}
    _write({"agent": agent, "phase": phase, **payload})


def log_node(agent: str, phase: str, state: dict[str, Any] | None = None) -> None:
    log_agent(agent, phase, state=_summarize_state(state))


def log_llm(
    agent: str,
    *,
    phase: str,
    messages: list[Any] | None = None,
    response: str | None = None,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    event: dict[str, Any] = {"agent": agent, "phase": phase}
    if model:
        event["model"] = model
    if messages is not None:
        event["messages"] = messages_to_dict(messages)
    if response is not None:
        event["response"] = _truncate(response)
    if extra:
        event.update(extra)
    _write(event)


def read_traces(
    session_id: str | None = None,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    if not DEBUG_DIR.is_dir():
        return []
    paths: list[Path]
    if session_id:
        path = DEBUG_DIR / f"{session_id}.jsonl"
        paths = [path] if path.is_file() else []
    else:
        paths = sorted(DEBUG_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    events: list[dict[str, Any]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if len(events) >= limit:
            break
    return events[-limit:]


def wrap_node(name: str, fn):
    """Wrap a LangGraph node to log enter/exit state."""

    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        log_node(name, "enter", state)
        result = fn(state)
        log_node(name, "exit", result)
        return result

    wrapped.__name__ = fn.__name__
    return wrapped
