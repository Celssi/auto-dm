"""Classify a DM turn so bookkeeping LLM calls can be skipped."""

from __future__ import annotations

from backend.dm.state import DMState

DICE_ONLY_TASKS = frozenset(
    {
        "ability_check",
        "saving_throw",
        "attack_roll",
        "initiative",
        "death_save",
        "oracle",
        "savage_attacker",
        "healer_medic",
    }
)


def is_dice_only_turn(state: DMState) -> bool:
    """True for a dedicated dice shortcut, not freeform text that mentions a roll."""
    shortcut = state.get("shortcut_result") or {}
    task = str(shortcut.get("task") or "")
    if task not in DICE_ONLY_TASKS:
        return False
    if state.get("precomputed_shortcut"):
        return True
    message = (state.get("user_message") or "").strip()
    return message.startswith("/")
