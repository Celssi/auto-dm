"""Per-session locks for read-modify-write of messages.json and character JSON."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

_meta = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def _lock_for(session_id: str) -> threading.Lock:
    with _meta:
        lock = _locks.get(session_id)
        if lock is None:
            lock = threading.Lock()
            _locks[session_id] = lock
        return lock


@contextmanager
def session_lock(session_id: str) -> Iterator[None]:
    lock = _lock_for(session_id)
    with lock:
        yield
