"""Tests for per-adventure Brambletrek curated module tables."""

from backend.games.brambletrek.modules.loader import (
    format_adventure_scene,
    format_module_journey_events,
    format_module_reason,
    journey_cards_for_adventure,
    load_module,
    lookup_module_journey_event,
    lookup_module_reason,
    module_ids,
    module_journey_tables,
)


def test_all_adventures_have_module_files():
    expected = {
        "world_tree",
        "dragonkeep",
        "pumpkin_party",
        "first_frost",
        "birthday_wonders",
        "winter_gift",
    }
    assert expected.issubset(set(module_ids()))


def test_world_tree_journey_and_reasons():
    mod = load_module("world_tree")
    assert mod.get("play", {}).get("journey_cards_per_day") == 3
    assert len(mod.get("reasons") or {}) == 13
    journeys = module_journey_tables("world_tree") or {}
    assert len(journeys.get("hearts") or {}) == 13
    event = lookup_module_journey_event("world_tree", "5 of hearts")
    assert event and event.get("morale") == 4
    reason = lookup_module_reason("world_tree", "2 of diamonds")
    assert reason and "Family Legacy" in str(reason.get("title", ""))
    text = format_module_reason("world_tree", "2 of diamonds")
    assert "Family Legacy" in text


def test_world_tree_format_journey_three_cards():
    cards = ["3 of hearts", "7 of diamonds", "9 of spades"]
    out = format_module_journey_events("world_tree", cards)
    assert "Heimstre" in out
    assert "3 of hearts" in out
    assert len(cards) == journey_cards_for_adventure("world_tree")


def test_first_frost_has_full_journey_grid():
    journeys = module_journey_tables("first_frost") or {}
    for suit in ("hearts", "diamonds", "clubs", "spades"):
        assert len(journeys.get(suit) or {}) == 13


def test_pumpkin_party_has_pie_tasting():
    mod = load_module("pumpkin_party")
    scenes = mod.get("scene_tables") or {}
    assert "pie_tasting" in scenes
    assert len(scenes.get("pie_tasting") or {}) >= 10


def test_pumpkin_party_choose_adventure_routing():
    out = format_adventure_scene(
        "pumpkin_party",
        ["5 of hearts", "jack of diamonds"],
        ["4 of hearts", "2 of diamonds"],
    )
    assert "Pumpkin Hunt" in out or "pumpkin_hunt" in out
    assert "Spirit" in out or "spirit" in out


def test_dragonkeep_exploration_table():
    out = format_adventure_scene(
        "dragonkeep",
        ["4 of hearts", "6 of clubs", "9 of spades"],
        scene_table="path_of_tempest",
    )
    assert "path of tempest" in out.lower() or "tempest" in out.lower()


def test_winter_gift_four_suits():
    journeys = module_journey_tables("winter_gift") or {}
    for suit in ("hearts", "diamonds", "clubs", "spades"):
        assert len(journeys.get(suit) or {}) == 13
