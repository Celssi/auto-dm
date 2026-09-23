"""Pytest hooks — disable LangSmith during automated tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"


@pytest.fixture
def isolated_saves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate all file persistence under a temporary saves root."""
    from backend.saves_paths import configure_saves_root

    configure_saves_root(tmp_path)
    for sub in ("characters", "adventures", "sessions", "campaigns"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "characters" / "roster.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "adventures" / "index.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "sessions" / "index.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "campaigns" / "index.json").write_text("[]\n", encoding="utf-8")
    yield tmp_path


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    from backend.tests.artifact_cleanup import cleanup_leaked_test_artifacts

    cleanup_leaked_test_artifacts()
