"""Chat LLM factory: Ollama (local) or Claude (Anthropic cloud)."""

from __future__ import annotations

import os
from typing import Any, Literal

from backend.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_CHAT_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_REQUEST_TIMEOUT,
)

ChatProvider = Literal["ollama", "claude"]

_CLAUDE_MODEL_ALIASES: dict[str, str] = {
    "claude-sonnet-4-20250514": "claude-sonnet-4-6",
}


def resolve_claude_model(model: str | None = None) -> str:
    name = (model or CLAUDE_CHAT_MODEL).strip()
    return _CLAUDE_MODEL_ALIASES.get(name, name)


def resolve_anthropic_api_key(*, anthropic_key: str | None = None) -> str | None:
    if anthropic_key and anthropic_key.strip():
        return anthropic_key.strip()
    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key
    return ANTHROPIC_API_KEY


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
    content = response.content if isinstance(response.content, str) else str(response.content)
    metadata = getattr(response, "response_metadata", None) or {}
    log_llm(
        agent,
        phase="response",
        response=content,
        model=model,
        extra={"provider": provider, "metadata": metadata},
    )
    return response


def get_langchain_chat_llm(provider: ChatProvider = "claude"):
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        key = resolve_anthropic_api_key()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return ChatAnthropic(
            model=resolve_claude_model(),
            api_key=key,
            max_tokens=8192,
        )
    from langchain_ollama import ChatOllama

    from backend.config import OLLAMA_BASE_URL

    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=os.environ.get("OLLAMA_CHAT_MODEL", "gemma3:12b"),
        timeout=OLLAMA_REQUEST_TIMEOUT,
    )


def get_llamaindex_chat_llm(provider: ChatProvider = "claude"):
    if provider == "claude":
        from llama_index.llms.anthropic import Anthropic

        key = resolve_anthropic_api_key()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return Anthropic(model=resolve_claude_model(), api_key=key, max_tokens=4096)
    from llama_index.llms.ollama import Ollama

    return Ollama(
        base_url=OLLAMA_BASE_URL,
        model=os.environ.get("OLLAMA_CHAT_MODEL", "gemma3:12b"),
        request_timeout=OLLAMA_REQUEST_TIMEOUT,
    )
