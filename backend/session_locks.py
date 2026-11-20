"""Per-session locks for read-modify-write of messages.json and character JSON."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

_meta = threading.Lock()
_locks: dict[str, threading.RLock] = {}


def _lock_for(key: str) -> threading.RLock:
    with _meta:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _locks[key] = lock
        return lock


@contextmanager
def session_lock(session_id: str) -> Iterator[None]:
    lock = _lock_for(f"session:{session_id}")
    with lock:
        yield


@contextmanager
def character_lock(character_id: str) -> Iterator[None]:
    lock = _lock_for(f"character:{character_id}")
    with lock:
        yield
