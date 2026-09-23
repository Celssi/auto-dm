"""World Tree guardian combat lookups."""

from backend.games.brambletrek.modules.combat import (
    build_combat_context,
    lookup_core_opponent,
    lookup_guardian,
)
from backend.games.brambletrek.modules.combat_data import world_tree_combat_section
from backend.games.brambletrek.modules.loader import load_module


def test_world_tree_yaml_guardians():
    mod = load_module("world_tree")
    combat = mod.get("combat") or world_tree_combat_section()
    hearts = (combat.get("guardians") or {}).get("hearts") or {}
    assert hearts.get("5", {}).get("label") == "Charging Boar"


def test_majestic_stag_hp_14():
    g = lookup_guardian("world_tree", "10 of hearts")
    assert g is not None
    assert g["label"] == "Majestic Stag"
    assert g["health"] == 14


def test_novice_thief_diamonds():
    g = lookup_guardian("world_tree", "2 of diamonds")
    assert g is not None
    assert g["label"] == "Novice Thief"
    assert g["health"] == 6


def test_clubs_not_guardian_suit():
    assert lookup_guardian("world_tree", "5 of clubs") is None


def test_clubs_core_combat_context():
    ctx = build_combat_context("world_tree", "5 of clubs", {"combat": True})
    assert ctx["type"] == "core"
    core = lookup_core_opponent("5 of clubs")
    assert core["health"] == 10
