"""Player-facing DM error copy. Never leak provider request ids or billing payloads."""

from __future__ import annotations

from typing import Any

CREDITS_MESSAGE = "The DM is unavailable right now (AI credits exhausted). Try again later."
BUSY_MESSAGE = "The DM is busy right now. Try again in a moment."
UNAVAILABLE_MESSAGE = "The DM is unavailable right now. Try again later."

_CREDITS_TOKENS = (
    "credit balance",
    "too low",
    "billing",
    "insufficient credit",
    "purchase credits",
    "plans & billing",
)
_BUSY_TOKENS = ("overloaded", "529", "rate limit", "429", "temporarily")
_AUTH_TOKENS = (
    "invalid x-api-key",
    "invalid api key",
    "authentication",
    "unauthorized",
    "401",
    "permission",
    "forbidden",
)
_PROVIDER_TOKENS = (
    "anthropic",
    "error code",
    "invalid_request_error",
    "api.anthropic",
    "claude",
    "llm",
    *_CREDITS_TOKENS,
    *_BUSY_TOKENS,
    *_AUTH_TOKENS,
)

_LAST_PROVIDER_ERROR: dict[str, Any] = {}


def _text(exc: BaseException | str) -> str:
    return str(exc or "")


def provider_error_class(exc: BaseException | str) -> str:
    text = _text(exc).lower()
    if any(token in text for token in _CREDITS_TOKENS):
        return "credits"
    if any(token in text for token in _BUSY_TOKENS):
        return "busy"
    if any(token in text for token in _AUTH_TOKENS):
        return "auth"
    if any(token in text for token in _PROVIDER_TOKENS):
        return "unavailable"
    return "error"


def is_provider_error(exc: BaseException | str) -> bool:
    text = _text(exc).lower()
    return any(token in text for token in _PROVIDER_TOKENS)


def friendly_dm_error(exc: BaseException | str) -> str:
    kind = provider_error_class(exc)
    if kind == "credits":
        return CREDITS_MESSAGE
    if kind == "busy":
        return BUSY_MESSAGE
    return UNAVAILABLE_MESSAGE


def record_provider_error(exc: BaseException | str) -> dict[str, Any]:
    import time

    payload = {
        "class": provider_error_class(exc),
        "ts": int(time.time()),
    }
    _LAST_PROVIDER_ERROR.clear()
    _LAST_PROVIDER_ERROR.update(payload)
    return dict(payload)


def last_provider_error() -> dict[str, Any]:
    return dict(_LAST_PROVIDER_ERROR)


def http_provider_error(exc: BaseException) -> Any:
    from fastapi import HTTPException

    record_provider_error(exc)
    return HTTPException(status_code=503, detail=friendly_dm_error(exc))
