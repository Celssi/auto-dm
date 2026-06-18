"""Tests for spoiler-safe narrative memory."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import backend.config as cfg
import backend.journal_storage as js
from backend.dm.story_memory import generate_opening_summary
from backend.dm.world_context import world_context_for_campaign


def test_world_context_for_narrator_omits_story_arc():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    js.CAMPAIGNS_DIR = tmpdir / "campaigns"
    js.CAMPAIGNS_INDEX = js.CAMPAIGNS_DIR / "index.json"
    js.CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)

    long_arc = "SECRET FUTURE PLOT " + "X" * 500
    js.save_campaign("test-camp", {"name": "Test", "story_arc": long_arc, "status": "active"})

    narrator_ctx = world_context_for_campaign("test-camp", for_narrator=True)
    bootstrap_ctx = world_context_for_campaign("test-camp", for_narrator=False)

    assert "SECRET FUTURE PLOT" not in narrator_ctx
    assert "SECRET FUTURE PLOT" in bootstrap_ctx


@patch("backend.dm.story_memory.invoke_chat_llm")
@patch("backend.dm.story_memory.get_langchain_chat_llm")
def test_generate_opening_summary_prompt_excludes_outline(mock_llm, mock_invoke):
    mock_response = MagicMock()
    mock_response.content = "## Current situation\nAt the inn."
    mock_invoke.return_value = mock_response
    mock_llm.return_value = MagicMock()

    generate_opening_summary(
        log="Hero arrived at the inn.",
        opening_scene="Rain fell on the cobblestones.",
        npc_hints="- Innkeeper: gruff",
    )

    call_args = mock_invoke.call_args[0][1]
    prompt = call_args[1].content
    assert "Adventure outline" not in prompt
    assert "Hero arrived" in prompt
    assert "document ONLY events" in prompt.lower() or "only events" in prompt.lower()
