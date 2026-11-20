"""Context-local sink for streaming narrator text during a DM turn."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

NarrationEmit = Callable[[str, object], None]

_SINK: ContextVar[NarrationEmit | None] = ContextVar("narration_sink", default=None)


@contextmanager
def narration_events(emit: NarrationEmit) -> Iterator[None]:
    token = _SINK.set(emit)
    try:
        yield
    finally:
        _SINK.reset(token)


def emit_narration(delta: str) -> None:
    sink = _SINK.get()
    if sink and delta:
        sink("narration", delta)


def emit_narration_replace(text: str) -> None:
    sink = _SINK.get()
    if sink:
        sink("narration_replace", text)


def emit_ready(payload: dict) -> None:
    """Unlock the play input once narrative text is final; post-processing continues."""
    sink = _SINK.get()
    if sink and payload:
        sink("ready", payload)


def emit_sheet(payload: dict) -> None:
    """Push the live character sheet as soon as resources are known."""
    sink = _SINK.get()
    if sink and payload:
        sink("sheet", payload)


def emit_logs(payload: dict) -> None:
    """Push lonelog/audit as soon as scribe/keeper finish, before slow journal work."""
    sink = _SINK.get()
    if sink and payload:
        sink("logs", payload)


def emit_world(payload: dict) -> None:
    """Ask the client to refresh NPCs/locations when the journal catch-up finishes."""
    sink = _SINK.get()
    if sink and payload:
        sink("world", payload)


def narration_enabled() -> bool:
    return _SINK.get() is not None
