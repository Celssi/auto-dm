"""Per-game compiled DM graphs."""

from __future__ import annotations

from backend.games.registry import get_game

_GRAPHS: dict[str, object] = {}


def get_dm_graph(game_id: str):
    if game_id not in _GRAPHS:
        _GRAPHS[game_id] = get_game(game_id).play.build_graph()
    return _GRAPHS[game_id]


def reset_dm_graphs() -> None:
    """Clear cached graphs (for tests)."""
    _GRAPHS.clear()
