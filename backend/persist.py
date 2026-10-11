"""Notify Cloud Storage after local save-file writes."""

from __future__ import annotations

from pathlib import Path


def after_write(path: Path) -> None:
    from backend.gcs_sync import upload_saves_path

    upload_saves_path(path)


def after_delete(path: Path) -> None:
    from backend.gcs_sync import delete_saves_path

    delete_saves_path(path)
