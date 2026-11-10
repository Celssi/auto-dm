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


def test_history_window_start_moves_in_steps():
    from backend.llm import history_window

    history = [{"role": "user", "content": str(i)} for i in range(22)]
    # Start index stays put for several turns, then jumps by the window step.
    starts = {n: history_window(history[:n])[0]["content"] for n in range(11, 22)}
    assert {starts[n] for n in range(11, 16)} == {"0"}
    assert {starts[n] for n in range(16, 22)} == {"6"}
    assert len(history_window(history[:8])) == 8
    assert all(len(history_window(history[:n])) >= 10 for n in range(10, 22))


def test_build_cached_chat_messages_puts_volatile_after_history():
    from langchain_core.messages import SystemMessage

    from backend.llm import build_cached_chat_messages

    msgs = build_cached_chat_messages(
        "rules",
        "world bible",
        [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
        "I open the door.",
        volatile="## Character\nHP 10/12",
    )
    assert isinstance(msgs[0], SystemMessage)
    blocks = msgs[0].content
    assert [b["text"] for b in blocks] == ["rules", "world bible"]
    assert "cache_control" in blocks[-1] and "cache_control" not in blocks[0]
    assert msgs[-2].content[-1]["cache_control"] == {"type": "ephemeral"}
    assert msgs[-1].content.startswith("## Character")
    assert msgs[-1].content.endswith("I open the door.")
    assert sum(isinstance(m, SystemMessage) for m in msgs) == 1
