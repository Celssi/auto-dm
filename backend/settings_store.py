"""User preferences persisted on disk."""

from __future__ import annotations

import json
from typing import Any

from backend.config import DATA_DIR

PREFS_PATH = DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "include_faerun": False,
    "use_rerank": True,
    "chat_model": "claude-opus-4-6",
}


def load_settings() -> dict[str, Any]:
    if not PREFS_PATH.is_file():
        return dict(DEFAULTS)
    try:
        data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data} if isinstance(data, dict) else dict(DEFAULTS)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    current.update({k: v for k, v in updates.items() if k in DEFAULTS})
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current
