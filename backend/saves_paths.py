"""Rebind file-storage roots (used by tests to isolate saves)."""

from __future__ import annotations

from pathlib import Path

import backend.config as config
import backend.journal_storage as journal_storage
import backend.storage as storage


def configure_saves_root(root: Path) -> None:
    """Point config, storage, and journal modules at the same saves directory."""
    root = Path(root)
    config.SAVES_DIR = root

    storage.SAVES_DIR = root
    storage.CHARACTERS_DIR = root / "characters"
    storage.CHARACTERS_INDEX = storage.CHARACTERS_DIR / "roster.json"
    storage.ADVENTURES_DIR = root / "adventures"
    storage.ADVENTURES_INDEX = storage.ADVENTURES_DIR / "index.json"
    storage.SESSIONS_DIR = root / "sessions"
    storage.SESSIONS_INDEX = storage.SESSIONS_DIR / "index.json"

    journal_storage.SAVES_DIR = root
    journal_storage.CAMPAIGNS_DIR = root / "campaigns"
    journal_storage.CAMPAIGNS_INDEX = journal_storage.CAMPAIGNS_DIR / "index.json"
