"""Game plugin registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException

DEFAULT_GAME_ID = "dnd5e"


@dataclass(frozen=True)
class GamePlugin:
    id: str
    label: str
    collection_name: str
    character_from_dict: Callable[..., Any]
    character_to_dict: Callable[..., dict[str, Any]]
    default_character: Callable[[], Any]
    rebuild_character: Callable[..., Any]
    character_creation_summary: Callable[..., dict[str, Any]]
    character_options_payload: Callable[..., dict[str, Any]]
    shortcuts: list[dict[str, str]]
    run_shortcut: Callable[..., dict[str, Any]]
    match_shortcut: Callable[[str], str | None]
    system_prompt: Callable[..., str]
    get_all_factions: Callable[[], list[str]]
    pdf_sources: dict[str, dict[str, str]]


def resolve_game_id(char_dict: dict[str, Any] | None) -> str:
    if not char_dict:
        return DEFAULT_GAME_ID
    gid = str(char_dict.get("game_id") or DEFAULT_GAME_ID).strip()
    return gid or DEFAULT_GAME_ID


def get_game(game_id: str | None = None) -> GamePlugin:
    from backend.games.dnd5e.plugin import DND5E_PLUGIN

    registry: dict[str, GamePlugin] = {DND5E_PLUGIN.id: DND5E_PLUGIN}
    gid = (game_id or DEFAULT_GAME_ID).strip() or DEFAULT_GAME_ID
    plugin = registry.get(gid)
    if not plugin:
        raise HTTPException(status_code=400, detail=f"Unknown game: {gid}")
    return plugin


def list_games() -> list[dict[str, str]]:
    return [{"id": g.id, "label": g.label} for g in [get_game(DEFAULT_GAME_ID)]]
