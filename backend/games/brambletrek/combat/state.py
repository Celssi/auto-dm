"""Brambletrek combat session state."""

from __future__ import annotations

from typing import Any

COMBAT_STATE_KEY = "brambletrek_combat"


def default_combat_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "mode": "standard",
        "adventure_id": "",
        "opponent": {"id": "", "label": "", "hp": 0, "max_hp": 0},
        "player": {"hp": 0},
        "initiative": {"player_card": "", "opponent_card": "", "first": "player"},
        "tactic_hand": [],
        "turn": "opponent",
        "finale_phase": "1",
        "phase_progress": {
            "damage_dealt": 0,
            "rounds": 0,
            "bands_seen": [],
            "eolan_red_streak": 0,
        },
        "buffs": {"damage_bonus": 0, "critical": False, "skip_player": 0, "halve_incoming_turns": 0},
        "log": [],
        "combat_context": None,
        "opponent_last_card": "",
        "item_used_this_phase": False,
        "combat_items": [],
        "can_search_item": False,
    }
