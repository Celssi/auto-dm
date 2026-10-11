"""SSE wrapper around a DM turn."""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Iterator
from typing import Any

from sse_starlette.sse import EventSourceResponse

from backend.dm.narration_stream import narration_events
from backend.dm.run_turn import run_dm_turn


def stream_dm_turn(
    session_id: str,
    user_message: str,
    *,
    precomputed_shortcut: dict | None = None,
    prelude: list[tuple[str, Any]] | None = None,
) -> EventSourceResponse:
    pending: queue.Queue[tuple[str, Any] | None] = queue.Queue()

    def emit(event: str, data: Any) -> None:
        pending.put((event, data))

    def worker() -> None:
        try:
            for event, data in prelude or []:
                emit(event, data)
            with narration_events(emit):
                result = run_dm_turn(
                    session_id,
                    user_message,
                    precomputed_shortcut=precomputed_shortcut,
                )
            if precomputed_shortcut:
                result = {**result, "shortcut": precomputed_shortcut}
            emit("done", result)
        except Exception as exc:
            emit("error", {"detail": str(exc)})
        finally:
            pending.put(None)

    def generate() -> Iterator[dict[str, str]]:
        threading.Thread(target=worker, daemon=True).start()
        while True:
            try:
                item = pending.get(timeout=15)
            except queue.Empty:
                yield {"event": "keepalive", "data": json.dumps({"ts": int(time.time())})}
                continue
            if item is None:
                break
            event, data = item
            yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(generate())
