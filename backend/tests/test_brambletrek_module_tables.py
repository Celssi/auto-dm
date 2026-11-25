"""Curated Brambletrek module tables match the book text (no empty or invented rows)."""

from __future__ import annotations

import pytest

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.manager import _lookup_player_tactic_row
from backend.games.brambletrek.modules.loader import (
    lookup_module_journey_event,
    lookup_module_scene_row,
    module_ids,
    module_journey_tables,
    module_path_locations,
    module_play_config,
    module_scene_tables,
)

SUITS = ("hearts", "diamonds", "spades", "clubs")


@pytest.mark.parametrize("adv", module_ids())
def test_no_empty_module_rows(adv):
    tables = module_journey_tables(adv) or {}
    for suit, rows in tables.items():
        if not isinstance(rows, dict):
            continue
        for rank, row in rows.items():
            if isinstance(row, dict):
                assert str(row.get("label") or "").strip(), (adv, suit, rank)
    for table_id, rows in module_scene_tables(adv).items():
        if not isinstance(rows, dict):
            continue
        for rank, row in rows.items():
            if isinstance(row, dict) and rank not in {"title", "intro"}:
                assert str(row.get("label") or "").strip(), (adv, table_id, rank)


def test_world_tree_face_cards_are_combat_and_new_rows():
    jt = module_journey_tables("world_tree")
    for suit in SUITS:
        for rank in ("jack", "queen", "king"):
            assert jt[suit][rank].get("combat") is True, (suit, rank)
        assert not jt[suit]["ace"].get("combat")
    assert "EXPLORATION" not in jt["hearts"]["ace"]["body"]
    assert jt["spades"]["5"]["health"] == -4 and jt["spades"]["5"]["supplies"] == -2
    assert jt["diamonds"]["8"]["supplies"] == 7
    assert jt["diamonds"]["8"]["label"].startswith("A cluster of glowing mushrooms")


def test_winter_gift_stats_from_book():
    jt = module_journey_tables("winter_gift")
    assert (jt["hearts"]["7"]["health"], jt["hearts"]["7"]["supplies"]) == (2, 2)
    assert jt["hearts"]["7"]["morale"] == 2 and "item" in jt["hearts"]["7"]["tags"]
    assert (jt["diamonds"]["6"]["health"], jt["diamonds"]["6"]["supplies"]) == (3, 3)
    assert "depths" in jt["clubs"]["7"]["tags"] and "depths" in jt["clubs"]["8"]["tags"]
    assert "depths" not in (jt["spades"]["7"].get("tags") or [])
    ace = lookup_module_scene_row("winter_gift", "surveyor_tactics", "ace of hearts")
    assert "SURVEYOR" not in ace["body"]


def test_birthday_typo_and_first_frost_rows():
    jt = module_journey_tables("birthday_wonders")
    assert "toast at the" in jt["diamonds"]["king"]["label"]
    assert jt["diamonds"]["4"]["morale"] == 2
    ev = lookup_module_journey_event("first_frost", "7 of spades")
    assert ev and ev.get("health") == -2 and ev.get("morale") == -1


def test_dragonkeep_path_locations_match_book():
    p = module_path_locations("dragonkeep")
    assert p["1"]["suit_outcomes"]["spades"]["health"] == -2  # Trees: falling branch
    assert p["3"]["suit_outcomes"]["hearts"]["supplies"] == 3  # Crates: preserved food
    assert "suit_outcomes" not in p["4"]  # Cave Door has no table
    assert p["5"]["suit_outcomes"]["clubs"].get("combat")  # Old Bonfire smoke
    assert p["7"]["suit_outcomes"]["diamonds"]["supplies"] == 2  # Duck Pond


def test_module_tactics_reach_combat():
    assert module_play_config("first_frost")["tactic_legacy"] == "snacker"
    char = BrambletrekCharacter(name="S", legacy="snacker", active_adventure="first_frost")
    row = _lookup_player_tactic_row(char, "5 of hearts")
    assert row and row.get("heal") == 4 and row["label"]


def test_module_tactic_fields_apply():
    from backend.games.brambletrek.combat.effects import apply_tactic_effects, damage_player

    state = {
        "player": {"hp": 10, "morale": 10, "max_hp": 20, "supplies": 9},
        "opponent": {"hp": 20},
        "buffs": {},
    }
    apply_tactic_effects(state, {"damage_formula": "half_supplies"}, actor="player")
    assert state["opponent"]["hp"] == 15  # half of 9 rounds up to 5
    apply_tactic_effects(state, {"halve_incoming_attacks": 2}, actor="player")
    damage_player(state, 6, [], source="opponent")
    assert state["player"]["hp"] == 7


def test_pumpkin_patch_journeys_from_book():
    jt = module_journey_tables("pumpkin_party")
    assert set(jt) == set(SUITS)
    assert all(len(jt[s]) == 13 for s in SUITS)
    assert jt["hearts"]["jack"]["combat"] is True
    assert jt["spades"]["ace"]["supplies"] == -4 and jt["spades"]["ace"]["health"] == -4
    assert module_play_config("pumpkin_party")["journey_cards_per_day"] == 4


def test_world_tree_items_use_artefacts_table():
    from backend.games.brambletrek.dm.curated import format_item_draw, lookup_item

    row = lookup_item("ace of spades", adventure_id="world_tree")
    assert row["label"] == "Blade of the Guardian"
    assert "Artefact" in format_item_draw("ace of spades", adventure_id="world_tree")
    # Other adventures keep the core Item Table.
    assert lookup_item("ace of spades")["label"] != "Blade of the Guardian"
    prophecy = lookup_module_scene_row("world_tree", "prophecy", "2 of clubs")
    assert prophecy["label"].startswith("Whispers soft")


def test_pumpkin_scene_is_festival_and_journey_day_is_patch():
    from backend.games.brambletrek.actions import _adventure_draw_plan

    assert _adventure_draw_plan("pumpkin_party") == (3, True, "")
    assert _adventure_draw_plan("pumpkin_party", for_scene=False) == (4, False, "")
    # Modules without a festival keep their journey plan either way.
    assert _adventure_draw_plan("winter_gift", for_scene=False) == _adventure_draw_plan(
        "winter_gift"
    )


def test_frozen_forest_tables_and_phase_lookup():
    from backend.games.brambletrek.modules.loader import (
        format_module_journey_events,
        load_module,
        lookup_module_journey_event,
        module_journey_tables,
    )

    celebration = module_journey_tables("first_frost") or {}
    forest = module_journey_tables("first_frost", "journeys_frozen_forest") or {}
    assert len(celebration.get("spades") or {}) == 13
    for suit in ("hearts", "diamonds", "clubs", "spades"):
        assert len(forest.get(suit) or {}) == 13
    # celebration 7 of spades is unchanged (p. 107)
    ev = lookup_module_journey_event("first_frost", "7 of spades")
    assert ev and ev.get("health") == -2 and ev.get("morale") == -1
    ff7 = lookup_module_journey_event(
        "first_frost", "7 of hearts", table_key="journeys_frozen_forest"
    )
    assert ff7 and ff7.get("supplies") == 7
    ace = lookup_module_journey_event(
        "first_frost", "ace of hearts", table_key="journeys_frozen_forest"
    )
    assert ace and ace.get("health") == 3 and ace.get("morale") == 3 and ace.get("supplies") == 3
    dia3 = lookup_module_journey_event(
        "first_frost", "3 of diamonds", table_key="journeys_frozen_forest"
    )
    assert dia3 and dia3.get("supplies") == 1 and dia3.get("health") == 2
    king = lookup_module_journey_event(
        "first_frost", "king of hearts", table_key="journeys_frozen_forest"
    )
    assert king and king.get("combat") and "through combat" in (king.get("body") or "")
    text = format_module_journey_events(
        "first_frost",
        ["7 of hearts"],
        table_key="journeys_frozen_forest",
    )
    assert "Adventures in the Frozen Forest" in text
    assert "The Warmth of the First Frost" in (
        load_module("first_frost").get("journey_heading") or ""
    )
    smores = (load_module("first_frost").get("scene_tables") or {}).get("smores_tactics") or {}
    assert smores["queen"]["halve_opponent_damage_round"] == "down"
    assert smores["ace"]["damage_formula"] == "draw_half_up"
    assert "rounded-down" in smores["queen"]["body"]
    assert "rounded up" in smores["ace"]["body"]


def test_begin_frozen_forest_shortcut_and_phase(isolated_saves):
    from backend.games.brambletrek.actions import (
        match_brambletrek_shortcut,
        run_shortcut,
        run_shortcut_for_plugin,
        shortcuts_for_character,
    )
    from backend.games.brambletrek.play_handlers import (
        FIRST_FROST_PHASE_KEY,
        begin_frozen_forest_phase,
    )
    from backend.storage import create_session

    assert match_brambletrek_shortcut("Begin Adventures in the Frozen Forest") == (
        "begin_frozen_forest"
    )
    labels = [s["id"] for s in shortcuts_for_character(active_adventure="first_frost")]
    assert "begin_frozen_forest" in labels
    run = run_shortcut("begin_frozen_forest", active_adventure="first_frost")
    assert "Frozen Forest" in run["user_message"]
    plugin = run_shortcut_for_plugin("begin_frozen_forest", active_adventure="first_frost")
    assert plugin.get("set_first_frost_phase") == "frozen_forest"
    sid = create_session(character_id="bt-frost", adventure_id="first_frost")
    out = begin_frozen_forest_phase(sid)
    assert out["first_frost_phase"] == "frozen_forest"
    from backend.storage import get_session

    extras = (get_session(sid) or {}).get("extras") or {}
    assert extras.get(FIRST_FROST_PHASE_KEY) == "frozen_forest"
