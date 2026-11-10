"""Chat LLM factory: Ollama (local) or Claude (Anthropic cloud)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_CHAT_MODEL,
    CLAUDE_SIDE_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_REQUEST_TIMEOUT,
)

ChatProvider = Literal["ollama", "claude"]
EffortLevel = Literal["high", "medium"]

_CLAUDE_MODEL_ALIASES: dict[str, str] = {
    "claude-sonnet-4-20250514": "claude-sonnet-4-6",
}

# Output cap per call. Adaptive thinking counts toward it, so keep headroom for long
# narration and large structured campaign plans.
CLAUDE_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "16000"))
# SDK-level retries with backoff on 429/5xx/overloaded, and a hard per-request timeout so
# a stuck upstream call cannot hold a Cloud Run request open forever.
CLAUDE_MAX_RETRIES = int(os.environ.get("CLAUDE_MAX_RETRIES", "3"))
CLAUDE_TIMEOUT_S = float(os.environ.get("CLAUDE_TIMEOUT_S", "600"))

# Narrator history: keep at least this many recent messages, but move the window start
# in steps so the cached conversation prefix stays identical across several turns.
HISTORY_MIN_MESSAGES = 10
HISTORY_WINDOW_STEP = 6


def resolve_claude_model(model: str | None = None) -> str:
    name = (model or CLAUDE_CHAT_MODEL).strip()
    return _CLAUDE_MODEL_ALIASES.get(name, name)


def resolve_claude_side_model() -> str:
    return resolve_claude_model(CLAUDE_SIDE_MODEL)


def resolve_anthropic_api_key(*, anthropic_key: str | None = None) -> str | None:
    if anthropic_key and anthropic_key.strip():
        return anthropic_key.strip()
    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key
    return ANTHROPIC_API_KEY


def message_text(response: Any) -> str:
    """Return visible prose from a chat response, skipping thinking blocks."""
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def cached_system(text: str) -> SystemMessage:
    """System prompt marked for Anthropic prompt caching."""
    return SystemMessage(
        content=[
            {
                "type": "text",
                "text": text,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    )


def history_window(history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Recent chat history with a start index that only moves every few turns.

    A plain ``[-10:]`` slice shifts the first message every turn, which changes the cached
    prefix and turns every narrator call into a full cache miss.
    """
    items = list(history or [])
    n = len(items)
    if n <= HISTORY_MIN_MESSAGES:
        return items
    start = ((n - HISTORY_MIN_MESSAGES) // HISTORY_WINDOW_STEP) * HISTORY_WINDOW_STEP
    return items[start:]


def build_cached_chat_messages(
    stable: str,
    variable: str,
    history: list[dict[str, Any]] | None,
    user_content: str,
    *,
    volatile: str = "",
) -> list[BaseMessage]:
    """Narrator prompt laid out for prompt caching.

    Order: [stable rules + session context] (cached) → history (cached at last message)
    → this turn's volatile context + player message (uncached). ``volatile`` is for
    state that changes nearly every turn (recent scenes, HP, canon summary) so it does not
    invalidate the cached prefix.
    """
    system_blocks: list[dict[str, Any]] = [{"type": "text", "text": stable}]
    if variable.strip():
        system_blocks.append({"type": "text", "text": variable.strip()})
    system_blocks[-1] = {**system_blocks[-1], "cache_control": {"type": "ephemeral"}}
    messages: list[BaseMessage] = [SystemMessage(content=system_blocks)]
    hist: list[BaseMessage] = []
    for item in history_window(history):
        role = item.get("role", "")
        content = item.get("content", "")
        if role == "user":
            hist.append(HumanMessage(content=content))
        elif role == "assistant":
            hist.append(AIMessage(content=content))
    if hist:
        hist[-1] = apply_cache_breakpoint(hist[-1])
    messages.extend(hist)
    turn = user_content
    if volatile.strip():
        turn = f"{volatile.strip()}\n\n## Player turn\n{user_content}"
    messages.append(HumanMessage(content=turn))
    return messages


def apply_cache_breakpoint(message: BaseMessage) -> BaseMessage:
    """Mark the last text block so a later turn can reuse this prefix."""
    content = message.content
    if isinstance(content, str):
        blocks: list[Any] = [
            {
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    elif isinstance(content, list):
        blocks = list(content)
        for i in range(len(blocks) - 1, -1, -1):
            block = blocks[i]
            if isinstance(block, str):
                blocks[i] = {
                    "type": "text",
                    "text": block,
                    "cache_control": {"type": "ephemeral"},
                }
                break
            if isinstance(block, dict) and block.get("type") == "text":
                blocks[i] = {**block, "cache_control": {"type": "ephemeral"}}
                break
        else:
            return message
    else:
        return message
    return message.model_copy(update={"content": blocks})


def _llm_model_name(llm: Any) -> str | None:
    for attr in ("model_name", "model"):
        value = getattr(llm, attr, None)
        if value:
            return str(value)
    return None


def invoke_chat_llm(
    llm: Any,
    messages: list[Any],
    *,
    agent: str,
    provider: ChatProvider = "claude",
) -> Any:
    """Invoke chat LLM with pipeline trace logging."""
    from backend.dm.trace import log_llm

    model = _llm_model_name(llm)
    log_llm(agent, phase="request", messages=messages, model=model, extra={"provider": provider})
    response = llm.invoke(messages)
    content = message_text(response)
    metadata = getattr(response, "response_metadata", None) or {}
    log_llm(
        agent,
        phase="response",
        response=content,
        model=model,
        extra={"provider": provider, "metadata": metadata},
    )
    return response


def stream_chat_llm(
    llm: Any,
    messages: list[Any],
    *,
    agent: str,
    provider: ChatProvider = "claude",
    on_text: Any | None = None,
) -> tuple[str, Any]:
    """Stream visible text deltas; return (full text, last chunk or assembled)."""
    from backend.dm.trace import log_llm

    model = _llm_model_name(llm)
    log_llm(agent, phase="request", messages=messages, model=model, extra={"provider": provider})
    parts: list[str] = []
    last: Any = None
    for chunk in llm.stream(messages):
        last = chunk
        delta = message_text(chunk)
        if not delta:
            continue
        parts.append(delta)
        if on_text:
            on_text(delta)
    text = "".join(parts)
    metadata = getattr(last, "response_metadata", None) or {} if last is not None else {}
    log_llm(
        agent,
        phase="response",
        response=text,
        model=model,
        extra={"provider": provider, "metadata": metadata},
    )
    return text, last


@lru_cache(maxsize=8)
def _cached_langchain_chat_llm(provider: str, model: str, api_key: str, effort: str):
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        kwargs: dict[str, Any] = {
            "model": model,
            "api_key": api_key,
            "max_tokens": CLAUDE_MAX_TOKENS,
            "max_retries": CLAUDE_MAX_RETRIES,
            "timeout": CLAUDE_TIMEOUT_S,
        }
        if effort:
            kwargs["effort"] = effort
        return ChatAnthropic(**kwargs)
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=model,
        timeout=OLLAMA_REQUEST_TIMEOUT,
    )


def get_langchain_chat_llm(
    provider: ChatProvider = "claude",
    *,
    effort: EffortLevel = "high",
    side: bool = False,
):
    """Chat model. ``side=True`` selects CLAUDE_SIDE_MODEL for bookkeeping calls."""
    if provider == "claude":
        key = resolve_anthropic_api_key()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        model = resolve_claude_side_model() if side else resolve_claude_model()
        return _cached_langchain_chat_llm(provider, model, key, effort)
    model = os.environ.get("OLLAMA_CHAT_MODEL", "gemma3:12b")
    return _cached_langchain_chat_llm(provider, model, "", "")


def structured_llm(schema: type, provider: ChatProvider = "claude", *, side: bool = True):
    """Structured output via json_schema (forced tool use is rejected on Opus 5.5).

    ``side=False`` keeps creative generation (campaigns, openings) on the main model.
    """
    return get_langchain_chat_llm(provider, effort="medium", side=side).with_structured_output(
        schema, method="json_schema"
    )


def get_llamaindex_chat_llm(provider: ChatProvider = "claude"):
    if provider == "claude":
        from llama_index.llms.anthropic import Anthropic

        key = resolve_anthropic_api_key()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return Anthropic(
            model=resolve_claude_model(),
            api_key=key,
            max_tokens=CLAUDE_MAX_TOKENS,
            max_retries=CLAUDE_MAX_RETRIES,
            timeout=CLAUDE_TIMEOUT_S,
            additional_kwargs={"output_config": {"effort": "high"}},
        )
    from llama_index.llms.ollama import Ollama

    return Ollama(
        base_url=OLLAMA_BASE_URL,
        model=os.environ.get("OLLAMA_CHAT_MODEL", "gemma3:12b"),
        request_timeout=OLLAMA_REQUEST_TIMEOUT,
    )
