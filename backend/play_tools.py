"""Dice rolling utilities."""

from __future__ import annotations

import random
import re
from typing import Any


def roll_dice(notation: str, *, caller: str = "unknown") -> dict[str, Any]:
    """Roll dice from notation like 1d20+5, 2d6, d20."""
    notation = notation.strip().lower().replace(" ", "")
    match = re.match(r"^(\d*)d(\d+)([+-]\d+)?$", notation)
    if not match:
        count = 1
        sides = 20
        modifier = 0
        if notation.isdigit():
            sides = int(notation)
        else:
            return {"ok": False, "summary": f"Invalid dice notation: {notation}"}
    else:
        count = int(match.group(1) or 1)
        sides = int(match.group(2))
        modifier = int(match.group(3) or 0)

    count = max(1, min(100, count))
    sides = max(2, min(1000, sides))
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    mod_str = f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else ""
    summary = f"**{notation}**: {rolls}{mod_str} = **{total}**"
    result = {"ok": True, "rolls": rolls, "modifier": modifier, "total": total, "summary": summary}

    from backend.dm.audit import audit_context, record_audit

    if audit_context().get("session_id"):
        source = caller.split(".")[0] if "." in caller else caller
        record_audit(
            {
                "event": "dice_roll",
                "source": source
                if source
                in (
                    "shortcut",
                    "combat_manager",
                    "character_builder",
                    "oracle",
                    "dice",
                )
                else "dice",
                "detail": {
                    "notation": notation,
                    "rolls": rolls,
                    "modifier": modifier,
                    "total": total,
                    "caller": caller,
                    "inferred": False,
                },
            }
        )

    return result


def format_dice_result(result: dict[str, Any]) -> str:
    return str(result.get("summary", ""))


# --- Playing card deck (Brambletrek and other card games) ---

_SUITS = ("hearts", "diamonds", "clubs", "spades")
_RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
_deck_store: dict[str, list[str]] = {}


def deck_scope_key(game_id: str, char_id: str | None = None) -> str:
    if char_id:
        return f"{game_id}:{char_id}"
    return game_id


def build_standard_deck() -> list[str]:
    cards = [f"{rank} of {suit}" for suit in _SUITS for rank in _RANKS]
    random.shuffle(cards)
    return cards


def _ensure_deck(scope_key: str) -> None:
    if scope_key not in _deck_store:
        _deck_store[scope_key] = build_standard_deck()


def deck_remaining(game_id: str, char_id: str | None = None) -> int:
    scope = deck_scope_key(game_id, char_id)
    _ensure_deck(scope)
    return len(_deck_store[scope])


def reset_deck(game_id: str, char_id: str | None = None) -> dict[str, Any]:
    scope = deck_scope_key(game_id, char_id)
    _deck_store[scope] = build_standard_deck()
    remaining = len(_deck_store[scope])
    return {
        "ok": True,
        "cards": [],
        "remaining": remaining,
        "summary": f"Deck reset and shuffled ({remaining} cards).",
    }


def draw_cards(
    count: int = 1,
    *,
    game_id: str = "brambletrek",
    char_id: str | None = None,
) -> dict[str, Any]:
    scope = deck_scope_key(game_id, char_id)
    if count < 1:
        return {
            "ok": False,
            "cards": [],
            "remaining": deck_remaining(game_id, char_id),
            "summary": "Draw count must be at least 1.",
        }
    _ensure_deck(scope)
    deck = _deck_store[scope]
    if len(deck) < count:
        return {
            "ok": False,
            "cards": deck.copy(),
            "remaining": len(deck),
            "summary": f"Not enough cards left (requested {count}, {len(deck)} remaining). Reset the deck.",
        }
    drawn = [deck.pop() for _ in range(count)]
    remaining = len(deck)
    if count == 1:
        summary = f"Drew **{drawn[0]}** ({remaining} cards left)."
    else:
        summary = f"Drew {count} cards: {', '.join(drawn)} ({remaining} cards left)."
    return {"ok": True, "cards": drawn, "remaining": remaining, "summary": summary}


def format_card_result(result: dict[str, Any]) -> str:
    return result.get("summary") or result.get("error") or "Card draw failed."


def clear_deck_store() -> None:
    _deck_store.clear()
