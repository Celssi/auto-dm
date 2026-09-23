"""Tests for GamePlayAdapter registration and hooks."""

from __future__ import annotations

from backend.games.registry import get_game


def test_dnd_play_adapter_pipeline():
    play = get_game("dnd5e").play
    assert play.rag_direct_tasks == frozenset({"rules_help"})
    assert play.supports_level_up is True
    assert play.supports_campaign_plan is True
    assert play.skip_chronicler is False
    graph = play.build_graph()
    assert graph is not None


def test_brambletrek_play_adapter_pipeline():
    play = get_game("brambletrek").play
    assert play.rag_direct_tasks == frozenset({"rag_direct"})
    assert play.supports_level_up is False
    assert play.supports_campaign_plan is False
    assert play.skip_chronicler is True
    assert play.skip_journal_keeper is True
    graph = play.build_graph()
    assert graph is not None


def test_dnd_shortcuts_for_character():
    play = get_game("dnd5e").play
    shortcuts = play.shortcuts_for_character({})
    assert any(s["id"] == "ability_check" for s in shortcuts)


def test_brambletrek_shortcuts_for_character():
    play = get_game("brambletrek").play
    shortcuts = play.shortcuts_for_character({"active_adventure": ""})
    assert any(s["id"] == "journey_day" for s in shortcuts)


def test_detect_shortcut_dnd_cast():
    play = get_game("dnd5e").play
    assert play.detect_shortcut("/cast fireball", {}) == "cast_spell"


def test_detect_shortcut_brambletrek_day():
    play = get_game("brambletrek").play
    assert play.detect_shortcut("/day", {}) == "journey_day"
