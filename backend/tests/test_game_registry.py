"""Tests for game plugin registry."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.games.brambletrek.characters.entity import default_character as bt_default
from backend.games.dnd5e.characters.entity import character_from_dict, default_character
from backend.games.registry import DEFAULT_GAME_ID, get_game, list_games, resolve_game_id


def test_get_game_dnd5e():
    plugin = get_game("dnd5e")
    assert plugin.id == "dnd5e"
    assert plugin.shortcuts
    assert plugin.collection_name
    assert plugin.play.supports_level_up is True
    assert plugin.play.build_graph() is not None


def test_get_game_brambletrek():
    plugin = get_game("brambletrek")
    assert plugin.id == "brambletrek"
    assert plugin.collection_name == "brambletrek_rules"
    assert plugin.shortcuts
    assert bt_default().game_id == "brambletrek"
    assert plugin.play.rag_direct_tasks == frozenset({"rag_direct"})


def test_get_game_unknown():
    with pytest.raises(HTTPException):
        get_game("shadowrun")


def test_resolve_game_id_defaults():
    assert resolve_game_id(None) == DEFAULT_GAME_ID
    assert resolve_game_id({}) == DEFAULT_GAME_ID
    assert resolve_game_id({"game_id": "dnd5e"}) == "dnd5e"


def test_character_from_dict_defaults_game_id():
    char = character_from_dict({"name": "Test"})
    assert char.game_id == "dnd5e"
    assert default_character().game_id == "dnd5e"


def test_list_games():
    games = list_games()
    assert any(g["id"] == "dnd5e" for g in games)
    assert any(g["id"] == "brambletrek" for g in games)
