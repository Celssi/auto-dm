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
    assert "Mist Veil" in tactic.get("label", "")


def test_face_card_tactic_jack():
    tactic = lookup_opponent_tactic("dragonkeep", "naiad", "jack of spades")
    assert tactic and tactic.get("band") == "jack"
    assert "Siren's Song" in tactic.get("label", "")


def test_exploration_face_card_jack():
    row = lookup_module_exploration_row("dragonkeep", "path_of_tempest", "jack of hearts")
    assert row is not None
    assert row.get("combat") is True


def test_water_elemental_and_naiad_tables_match_book():
    we = lookup_opponent_tactic("dragonkeep", "water_elemental", "2 of hearts")
    na = lookup_opponent_tactic("dragonkeep", "naiad", "2 of clubs")
    assert we and we.get("label", "").startswith("Ripple Strike")
    assert na and na.get("label", "").startswith("Soothing Melody")
    ace = lookup_opponent_tactic("dragonkeep", "water_elemental", "ace of spades")
    assert ace and "Torrential Wrath" in ace.get("label", "")


def test_king_crab_dangerous_waters_is_player_dot():
    tactic = lookup_opponent_tactic("dragonkeep", "king_crab", "queen of hearts")
    assert tactic and tactic.get("player_dot_damage") == 2
    assert tactic.get("player_dot_turns") == 3


def test_enchanted_treant_sap_coating_is_armor():
    tactic = lookup_opponent_tactic("dragonkeep", "enchanted_treant", "6 of diamonds")
    assert tactic and tactic.get("opponent_armor") == 3
    assert "reduce_player_damage" not in tactic or not tactic.get("reduce_player_damage")


def test_enchanted_treant_timber_smash_self_damage():
    tactic = lookup_opponent_tactic("dragonkeep", "enchanted_treant", "king of clubs")
    assert tactic and tactic.get("damage") == 7 and tactic.get("self_damage") == 4


def test_fire_elemental_book_tactics():
    jack = lookup_opponent_tactic("dragonkeep", "fire_elemental", "jack of hearts")
    queen = lookup_opponent_tactic("dragonkeep", "fire_elemental", "queen of hearts")
    ace = lookup_opponent_tactic("dragonkeep", "fire_elemental", "ace of hearts")
    assert jack and jack.get("reduce_player_damage") == 1
    assert jack.get("reduce_player_damage_until_end")
    assert queen and queen.get("destroy_last_item")
    assert ace and ace.get("damage") == 5 and ace.get("reduce_player_damage_turns") == 3
