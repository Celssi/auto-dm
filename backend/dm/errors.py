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


INTERNAL_MESSAGE = "Something went wrong on the server ({kind}). The error has been logged."

# Exception classes raised by provider SDKs (anthropic / langchain-anthropic / httpx).
_PROVIDER_MODULE_PREFIXES = ("anthropic", "langchain_anthropic", "httpx", "httpcore", "openai")


def _is_provider_exception(exc: BaseException) -> bool:
    for cls in type(exc).__mro__:
        module = getattr(cls, "__module__", "") or ""
        if module.startswith(_PROVIDER_MODULE_PREFIXES):
            return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    return provider_error_class(exc) != "error"


def http_provider_error(exc: BaseException, *, context: str = "") -> Any:
    """Map an exception to an HTTPException, logging type + traceback first.

    Only real provider failures (Anthropic SDK / network / credits / rate limit) become the
    friendly 503 "DM unavailable". Code bugs become a 500 that names the exception type so
    they are not hidden behind the provider message.
    """
    import logging

    from fastapi import HTTPException

    log = logging.getLogger("backend.dm.errors")
    where = f" in {context}" if context else ""
    log.error(
        "DM request failed%s: %s: %s",
        where,
        type(exc).__name__,
        _text(exc)[:500],
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    if _is_provider_exception(exc):
        record_provider_error(exc)
        return HTTPException(status_code=503, detail=friendly_dm_error(exc))
    payload = record_provider_error(exc)
    payload["exception"] = type(exc).__name__
    _LAST_PROVIDER_ERROR.update(payload)
    return HTTPException(status_code=500, detail=INTERNAL_MESSAGE.format(kind=type(exc).__name__))
