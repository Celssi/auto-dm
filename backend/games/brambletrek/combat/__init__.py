"""Brambletrek card-based combat loop."""

from backend.games.brambletrek.combat.manager import (
    begin_combat,
    combat_action,
    combat_payload,
    end_combat,
)

__all__ = ["begin_combat", "combat_action", "combat_payload", "end_combat"]
