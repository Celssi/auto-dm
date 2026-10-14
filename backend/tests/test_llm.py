"""Unit tests for Claude response text and prompt-cache helpers."""

from __future__ import annotations

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from backend.llm import apply_cache_breakpoint, cached_system, message_text


def test_message_text_skips_thinking_blocks():
    response = SimpleNamespace(
        text=None,
        content=[
            {"type": "thinking", "thinking": "plan the scene"},
            {"type": "text", "text": "The tavern door creaks open."},
        ],
    )
    assert message_text(response) == "The tavern door creaks open."


def test_message_text_uses_string_text_property():
    response = SimpleNamespace(
        text="Only the prose.", content=[{"type": "thinking", "thinking": "hidden"}]
    )
    assert message_text(response) == "Only the prose."


def test_cached_system_adds_ephemeral_breakpoint():
    message = cached_system("You are the Dungeon Master.")
    assert isinstance(message.content, list)
    assert message.content[0]["type"] == "text"
    assert message.content[0]["text"] == "You are the Dungeon Master."
    assert message.content[0]["cache_control"] == {"type": "ephemeral"}


def test_apply_cache_breakpoint_marks_last_text_block():
    marked = apply_cache_breakpoint(HumanMessage(content="I search the room."))
    assert marked.content[0]["cache_control"] == {"type": "ephemeral"}
    assistant = apply_cache_breakpoint(
        AIMessage(content=[{"type": "text", "text": "Dust motes hang in the air."}])
    )
    assert assistant.content[0]["cache_control"] == {"type": "ephemeral"}
