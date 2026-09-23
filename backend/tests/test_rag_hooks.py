"""Tests for per-game RAG hooks."""

from __future__ import annotations

from backend.games.registry import get_game


def test_dnd_rag_hooks_are_noop_enhancements():
    hooks = get_game("dnd5e").rag
    assert hooks.enhance_query is None
    assert hooks.boost_retrieval is None
    assert "D&D 5e" in hooks.system_prompt(["player", "dm"])


def test_brambletrek_rag_hooks_present():
    hooks = get_game("brambletrek").rag
    assert hooks.enhance_query is not None
    assert hooks.boost_retrieval is not None
    assert hooks.run_ingest is not None
    assert "brambletrek" in hooks.ingest_hint
    assert "Brambletrek" in hooks.system_prompt(["core"])
