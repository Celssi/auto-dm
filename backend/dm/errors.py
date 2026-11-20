"""Player-facing DM error copy. Never leak provider request ids or billing payloads."""

from __future__ import annotations

CREDITS_MESSAGE = "The DM is unavailable right now (AI credits exhausted). Try again later."
BUSY_MESSAGE = "The DM is busy right now. Try again in a moment."
UNAVAILABLE_MESSAGE = "The DM is unavailable right now. Try again later."


def friendly_dm_error(exc: BaseException | str) -> str:
    text = str(exc or "").lower()
    if any(token in text for token in ("credit balance", "too low", "billing", "insufficient credit")):
        return CREDITS_MESSAGE
    if any(token in text for token in ("overloaded", "529", "rate limit", "429", "temporarily")):
        return BUSY_MESSAGE
    return UNAVAILABLE_MESSAGE
