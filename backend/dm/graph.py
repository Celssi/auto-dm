"""DM graph — backward-compatible re-exports after per-game pipeline split."""

from __future__ import annotations

from typing import Any

from backend.dm.graph_factory import get_dm_graph
from backend.dm.nodes.bookkeeping import character_keeper_node
from backend.dm.run_turn import run_dm_turn
from backend.dm.state import DMState, char_from_dict, game_plugin
from backend.games.dnd5e.characters.character_builder import (
    character_creation_summary,
    level_up,
)
from backend.games.dnd5e.dm.agents.nodes import resource_keeper_node
from backend.storage import get_character, save_character


def level_up_character(
    char_id: str,
    hp_roll: int | None = None,
    class_name: str | None = None,
) -> dict[str, Any]:
    char = get_character(char_id)
    if not char:
        raise ValueError("Character not found")
    plugin = game_plugin(char)
    obj = level_up(
        plugin.rebuild_character(char_from_dict(char)), hp_roll=hp_roll, class_name=class_name
    )
    saved = plugin.character_to_dict(obj)
    save_character(char_id, saved)
    return {"character": saved, "summary": character_creation_summary(obj)}


__all__ = [
    "DMState",
    "character_keeper_node",
    "get_dm_graph",
    "level_up_character",
    "resource_keeper_node",
    "run_dm_turn",
]
