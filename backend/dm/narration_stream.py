"""Context-local sink for streaming narrator text during a DM turn."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

NarrationEmit = Callable[[str, str], None]

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


def narration_enabled() -> bool:
    return _SINK.get() is not None
