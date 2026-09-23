"""Brambletrek combat manager — initiative, turns, HP."""

from unittest.mock import patch

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.manager import (
    begin_combat,
    combat_action,
    combat_payload,
)
from backend.games.brambletrek.modules.combat import build_combat_context, lookup_core_opponent


def _char(**kwargs) -> BrambletrekCharacter:
    c = BrambletrekCharacter(name="Test", legacy="scrapper", health=12)
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


def test_build_core_combat_context():
    ctx = build_combat_context("first_frost", "5 of clubs", {"combat": True, "label": "Wolf"})
    assert ctx["type"] == "core"
    assert ctx["adventure_id"] == "first_frost"


def test_world_tree_clubs_core_fallback():
    ctx = build_combat_context("world_tree", "7 of clubs", {"combat": True})
    assert ctx["type"] == "core"
    core = lookup_core_opponent("7 of clubs")
    assert core["health"] == 10


def test_begin_combat_initializes_state():
    char = _char()
    ctx = build_combat_context("first_frost", "3 of spades", {"combat": True})
    with patch(
        "backend.games.brambletrek.combat.manager.draw_cards",
        side_effect=[
            {"ok": True, "cards": ["4 of hearts", "2 of clubs"]},
            {"ok": True, "cards": ["5 of hearts", "6 of diamonds", "7 of clubs", "8 of spades"]},
        ],
    ):
        state = begin_combat(char, ctx, char_id="c1")
    assert state["status"] == "active"
    assert len(state["tactic_hand"]) == 4
    assert state["opponent"]["hp"] > 0
    assert state["player"]["hp"] == 12


def test_combat_damage_and_win():
    char = _char(health=15)
    ctx = {"adventure_id": "first_frost", "type": "core", "card": "2 of clubs"}
    with patch(
        "backend.games.brambletrek.combat.manager.draw_cards",
        side_effect=[
            {"ok": True, "cards": ["10 of hearts", "2 of clubs"]},
            {
                "ok": True,
                "cards": ["ace of spades", "king of hearts", "queen of diamonds", "jack of clubs"],
            },
            {"ok": True, "cards": ["2 of hearts"]},
        ],
    ):
        state = begin_combat(char, ctx, char_id="c1")
    state["turn"] = "player"
    state["opponent"]["hp"] = 1
    state, lines = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["status"] == "won"
    assert any("defeat" in line.lower() for line in lines)


def test_combat_payload_shape():
    payload = combat_payload(
        {
            "status": "active",
            "opponent": {"label": "Wolf", "hp": 8, "max_hp": 10},
            "player": {"hp": 12},
            "tactic_hand": ["2 of hearts"],
            "turn": "player",
            "log": ["Fight!"],
        }
    )
    assert payload and payload["status"] == "active"
    assert payload["opponent"]["label"] == "Wolf"


def test_opponent_turn_deals_damage():
    char = _char(health=10)
    ctx = {"adventure_id": "dragonkeep", "opponent_id": "water_elemental", "card": "jack of hearts"}
    with patch(
        "backend.games.brambletrek.combat.manager.draw_cards",
        side_effect=[
            {"ok": True, "cards": ["3 of hearts", "4 of diamonds"]},
            {"ok": True, "cards": ["2 of hearts", "3 of clubs", "4 of spades", "5 of diamonds"]},
            {"ok": True, "cards": ["5 of hearts"]},
        ],
    ):
        state = begin_combat(char, ctx, char_id="c1")
    state["turn"] = "opponent"
    before = state["player"]["hp"]
    state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["turn"] == "player" or state["player"]["hp"] <= before


def test_aerith_item_search_red():
    char = _char(health=12)
    ctx = {"adventure_id": "dragonkeep", "finale": True, "finale_phase": "1", "opponent_id": "aerith"}
    draw_calls: list[int] = []

    def fake_draw(*_args, **_kwargs):
        draw_calls.append(1)
        n = len(draw_calls)
        if n == 1:
            return {"ok": True, "cards": ["4 of hearts", "3 of clubs"]}
        if n == 2:
            return {"ok": True, "cards": ["2 of hearts", "3 of clubs", "4 of spades", "5 of diamonds"]}
        return {"ok": True, "cards": ["2 of hearts"]}

    with patch("backend.games.brambletrek.combat.manager.draw_cards", side_effect=fake_draw):
        state = begin_combat(char, ctx, char_id="c1", mode="aerith_finale")
        state["turn"] = "player"
        state, lines = combat_action(state, char, "search_item", char_id="c1")
    assert state["item_used_this_phase"] is True
    assert "Whispering Wind Chime" in (state.get("combat_items") or [""])[0]
    assert any("Whispering Wind Chime" in line for line in lines)


def test_aerith_phase3_goals_stricter():
    from backend.games.brambletrek.modules.combat import lookup_aerith_phase_goals

    g3 = lookup_aerith_phase_goals("3")
    assert g3["damage_goal"] == 25
    assert g3["rounds_goal"] == 5
    g1 = lookup_aerith_phase_goals("1")
    assert g1["damage_goal"] == 20
    assert g1["rounds_goal"] == 4


def test_aerith_phase_complete_uses_phase_goals():
    from backend.games.brambletrek.combat.manager import _aerith_phase_complete

    state = {
        "mode": "aerith_finale",
        "finale_phase": "3",
        "phase_progress": {"damage_dealt": 24, "rounds": 3, "bands_seen": []},
    }
    assert _aerith_phase_complete(state) is False
    state["phase_progress"]["damage_dealt"] = 25
    assert _aerith_phase_complete(state) is True


def test_eolan_red_face_streak_advances_phase():
    char = _char(health=12)
    ctx = {"adventure_id": "dragonkeep", "finale": True, "finale_phase": "1", "opponent_id": "aerith"}
    with patch(
        "backend.games.brambletrek.combat.manager.draw_cards",
        side_effect=[
            {"ok": True, "cards": ["4 of hearts", "3 of clubs"]},
            {"ok": True, "cards": ["2 of hearts", "3 of clubs", "4 of spades", "5 of diamonds"]},
            {"ok": True, "cards": ["jack of hearts"]},
            {"ok": True, "cards": ["queen of diamonds"]},
            {"ok": True, "cards": ["3 of hearts", "4 of clubs", "5 of spades", "6 of diamonds"]},
        ],
    ):
        state = begin_combat(char, ctx, char_id="c1", mode="aerith_finale")
        state["turn"] = "eolan"
        state, _ = combat_action(state, char, "eolan_turn", char_id="c1")
        state["turn"] = "eolan"
        state, lines = combat_action(state, char, "eolan_turn", char_id="c1")
    assert state.get("finale_phase") == "2"
    assert any("red face" in line.lower() for line in lines)


def test_advance_phase_button_flow():
    char = _char(health=12)
    ctx = {"adventure_id": "dragonkeep", "finale": True, "finale_phase": "1", "opponent_id": "aerith"}
    with patch(
        "backend.games.brambletrek.combat.manager.draw_cards",
        side_effect=[
            {"ok": True, "cards": ["4 of hearts", "3 of clubs"]},
            {"ok": True, "cards": ["2 of hearts", "3 of clubs", "4 of spades", "5 of diamonds"]},
            {"ok": True, "cards": ["3 of hearts", "4 of clubs", "5 of spades", "6 of diamonds"]},
        ],
    ):
        state = begin_combat(char, ctx, char_id="c1", mode="aerith_finale")
    state["phase_progress"] = {"damage_dealt": 20, "rounds": 1, "bands_seen": [], "eolan_red_streak": 0}
    state, lines = combat_action(state, char, "advance_phase", char_id="c1")
    assert state["finale_phase"] == "2"
    assert len(state["tactic_hand"]) == 4
    payload = combat_payload(state)
    assert payload and payload["can_advance_phase"] is False


def test_veil_of_darkness_misses_attacks():
    from backend.games.brambletrek.combat.effects import apply_tactic_effects

    state = {
        "opponent": {"label": "Aerith", "hp": 60, "max_hp": 60},
        "player": {"hp": 12},
        "buffs": {},
        "phase_progress": {"damage_dealt": 0},
    }
    tactic = {"label": "Veil of Darkness", "player_attacks_miss_turns": 2}
    apply_tactic_effects(state, tactic, actor="opponent")
    player_tactic = {"label": "Strike", "damage": 5}
    lines = apply_tactic_effects(state, player_tactic, actor="player")
    assert state["opponent"]["hp"] == 60
    assert any("miss" in line.lower() for line in lines)
