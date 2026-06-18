"""Tests for narrative memory assembly (no LLM)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import backend.config as cfg
import backend.journal_storage as js
from backend.characters.entity import character_from_dict
from backend.dm.story_memory import build_narrative_context, build_offline_summary, recent_scenes_from_log
from backend.dm.world_context import world_context_for_campaign


def test_recent_scenes_from_log():
    log = """# Log

### 2025-01-01 10:00:00

First event happened.

### 2025-01-02 11:00:00

Second event with more detail.
"""
    recent = recent_scenes_from_log(log, max_entries=10)
    assert "First event" in recent
    assert "Second event" in recent


def test_build_narrative_context_layers():
    char = character_from_dict({"name": "Test", "campaign_notes": "Pinehaven"})
    adventure = {
        "summary": "## Current situation\nHero at the inn.",
        "log": "### 2025-01-01 10:00:00\n\nArrived at inn.\n",
    }
    ctx = build_narrative_context(adventure, None, char)
    assert "Current situation" in ctx["canon_summary"]
    assert "Arrived at inn" in ctx["recent_scenes"]
    assert "continue naturally" in ctx["recent_scenes"].lower()


def test_world_context_shortens_arc_when_summary_exists():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    js.CAMPAIGNS_DIR = tmpdir / "campaigns"
    js.CAMPAIGNS_INDEX = js.CAMPAIGNS_DIR / "index.json"
    js.CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)

    long_arc = "A" * 3000
    js.save_campaign("test-camp", {"name": "Test", "story_arc": long_arc, "status": "active"})

    with_summary = world_context_for_campaign("test-camp", has_adventure_summary=True)
    without_summary = world_context_for_campaign("test-camp", has_adventure_summary=False)

    assert len(with_summary) < len(without_summary)


def test_build_offline_summary_from_log():
    log = "### 2025-01-01 10:00:00\n\nHero arrived.\n\n### 2025-01-02 11:00:00\n\nFestival began.\n"
    summary = build_offline_summary(log=log, outline="# Test adventure")
    assert "## Current situation" in summary
    assert "Festival began" in summary
    assert "Hero arrived" in summary

    from backend.dm.continuity_guard import apply_continuity_guard

    result, issues = apply_continuity_guard(
        draft_response="",
        user_message="hello",
        canon_summary="",
        world_bible="",
        recent_scenes="",
    )
    assert result == ""
    assert issues == []


def test_continuity_guard_node_skips_rules_help():
    from backend.dm.graph import continuity_guard_node

    state = {
        "shortcut_result": {"task": "rules_help"},
        "narrative": "Rules text",
        "response": "Rules text",
    }
    assert continuity_guard_node(state) == {}
