"""Persisted PDF reader bookmarks and last-read page."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.config import SAVES_DIR

BOOKS_PATH = SAVES_DIR / "books.json"

DEFAULT_STATE: dict[str, Any] = {
    "bookmarks": [],
    "lastByGame": {},
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clean_bookmark(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    book_id = str(raw.get("book_id") or "").strip()
    try:
        page = int(raw.get("page"))
    except (TypeError, ValueError):
        return None
    if not book_id or page < 1:
        return None
    label = str(raw.get("label") or "").strip()
    created = str(raw.get("created_at") or "").strip() or _now()
    bookmark_id = str(raw.get("id") or "").strip() or uuid.uuid4().hex[:12]
    return {
        "id": bookmark_id,
        "book_id": book_id,
        "page": page,
        "label": label,
        "created_at": created,
    }


def _clean_last(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    book_id = str(raw.get("book_id") or "").strip()
    try:
        page = int(raw.get("page"))
    except (TypeError, ValueError):
        return None
    if not book_id or page < 1:
        return None
    return {"book_id": book_id, "page": page}


def load_book_state() -> dict[str, Any]:
    if not BOOKS_PATH.is_file():
        return {"bookmarks": [], "lastByGame": {}}
    try:
        data = json.loads(BOOKS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"bookmarks": [], "lastByGame": {}}
    if not isinstance(data, dict):
        return {"bookmarks": [], "lastByGame": {}}
    bookmarks = [_clean_bookmark(item) for item in data.get("bookmarks") or []]
    last_raw = data.get("lastByGame")
    last: dict[str, Any] = {}
    if isinstance(last_raw, dict):
        for game_id, entry in last_raw.items():
            cleaned = _clean_last(entry)
            if cleaned:
                last[str(game_id)] = cleaned
    return {"bookmarks": [item for item in bookmarks if item], "lastByGame": last}


def save_book_state(updates: dict[str, Any]) -> dict[str, Any]:
    current = load_book_state()
    if "bookmarks" in updates:
        bookmarks = [_clean_bookmark(item) for item in updates.get("bookmarks") or []]
        current["bookmarks"] = [item for item in bookmarks if item]
    if "lastByGame" in updates:
        last: dict[str, Any] = {}
        raw = updates.get("lastByGame") or {}
        if isinstance(raw, dict):
            for game_id, entry in raw.items():
                cleaned = _clean_last(entry)
                if cleaned:
                    last[str(game_id)] = cleaned
        current["lastByGame"] = last
    BOOKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOOKS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    from backend.persist import after_write

    after_write(BOOKS_PATH)
    return current
