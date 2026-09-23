"""Dragonkeep module combat lookups."""

from backend.games.brambletrek.modules.combat import (
    lookup_opponent,
    lookup_opponent_tactic,
    resolve_dragonkeep_opponent,
)
from backend.games.brambletrek.modules.combat_data import dragonkeep_combat_section
from backend.games.brambletrek.modules.loader import load_module, lookup_module_exploration_row


def test_dragonkeep_yaml_has_combat():
    mod = load_module("dragonkeep")
    combat = mod.get("combat") or dragonkeep_combat_section()
    assert combat.get("opponents")
    assert combat.get("opponent_by_rank")


def test_tempest_jack_maps_water_elemental():
    opp = resolve_dragonkeep_opponent("path_of_tempest", "jack of hearts")
    assert opp == "water_elemental"


def test_tempest_queen_maps_naiad():
    opp = resolve_dragonkeep_opponent("path_of_tempest", "queen of diamonds")
    assert opp == "naiad"


def test_tempest_king_maps_king_crab():
    opp = resolve_dragonkeep_opponent("path_of_tempest", "king of spades")
    assert opp == "king_crab"


def test_pyre_opponents():
    assert resolve_dragonkeep_opponent("path_of_pyre", "jack of clubs") == "fire_elemental"
    assert resolve_dragonkeep_opponent("path_of_pyre", "queen of hearts") == "molten_golem"
    assert resolve_dragonkeep_opponent("path_of_pyre", "king of diamonds") == "firebird"


def test_leaf_rank_9_forest_elemental():
    assert resolve_dragonkeep_opponent("path_of_leaf", "9 of hearts") == "forest_elemental"


def test_water_elemental_tactic_band():
    opp = lookup_opponent("dragonkeep", "water_elemental")
    assert opp and opp.get("health") == 14
    tactic = lookup_opponent_tactic("dragonkeep", "water_elemental", "5 of hearts")
    assert tactic and tactic.get("band") == "5-7"
    assert "Aqua Dart" in tactic.get("label", "")


def test_face_card_tactic_jack():
    tactic = lookup_opponent_tactic("dragonkeep", "naiad", "jack of spades")
    assert tactic and tactic.get("band") == "jack"
    assert "Whirlpool" in tactic.get("label", "")


def test_exploration_face_card_jack():
    row = lookup_module_exploration_row("dragonkeep", "path_of_tempest", "jack of hearts")
    assert row is not None
    assert row.get("combat") is True
