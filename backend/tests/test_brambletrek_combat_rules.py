"""Brambletrek combat per the Core Rulebook (pp. 8, 16, 28, 30-32)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.effects import apply_tactic_effects, half_up
from backend.games.brambletrek.combat.manager import begin_combat, combat_action
from backend.games.brambletrek.dm.curated import lookup_player_tactic

MANAGER = "backend.games.brambletrek.combat.manager.draw_cards"


def _char(**kw) -> BrambletrekCharacter:
    c = BrambletrekCharacter(name="T", legacy="scrapper", health=15, morale=12, supplies=10)
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def _deck(*draws: list[str]):
    seq = [{"ok": True, "cards": list(d), "remaining": 40} for d in draws]
    return patch(MANAGER, side_effect=seq)


def _start(char, ctx_card="jack of clubs", init=("10 of hearts", "2 of clubs"), hand=None):
    hand = hand or ["3 of hearts", "4 of hearts", "5 of hearts", "6 of hearts"]
    ctx = {"adventure_id": "", "type": "core", "card": ctx_card}
    with _deck(list(init), hand):
        return begin_combat(char, ctx, char_id="c1")


def test_half_up_rounds_up():
    assert half_up(11) == 6
    assert half_up(7) == 4
    assert half_up(4) == 2


def test_every_player_tactic_has_label_and_mechanic():
    for legacy in ("seer", "scrapper", "storyteller", "seeker", "sneaker", "soother"):
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace"):
            row = lookup_player_tactic(legacy, f"{rank} of hearts")
            assert row and row["label"], (legacy, rank)
            mechanics = set(row) - {"label", "effect", "legacy", "rank_key", "card"}
            assert mechanics, (legacy, rank)


def test_initiative_higher_goes_first_and_hand_of_four():
    state = _start(_char(), init=("2 of hearts", "king of clubs"))
    assert state["turn"] == "opponent"
    assert len(state["tactic_hand"]) == 4
    assert state["opponent"]["hp"] == 10  # Jack = 10 Health (p. 30)


def test_core_opponent_numeric_card_deals_damage():
    """Bug: numeric opponent cards used a band key and dealt nothing."""
    char = _char(health=15)
    state = _start(char, init=("2 of hearts", "king of clubs"))
    with _deck(["8 of spades"]):  # Vicious Bite: 4 damage
        state, lines = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["player"]["hp"] == 11
    assert char.health == 11
    assert any("Vicious Bite" in line for line in lines)


def test_rapid_cut_half_of_drawn_card_rounded_up():
    char = _char(health=15)
    state = _start(char, init=("2 of hearts", "king of clubs"))
    with _deck(["4 of spades"], ["ace of hearts"]):
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["player"]["hp"] == 15 - 6


def test_scrapper_haymaker_and_dodge():
    char = _char()
    state = _start(char, hand=["3 of hearts", "2 of hearts", "5 of clubs", "6 of clubs"])
    hp0 = state["opponent"]["hp"]
    state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)  # Haymaker 4
    assert state["opponent"]["hp"] == hp0 - 4
    with _deck(["8 of spades"]):
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["player"]["hp"] == 11
    state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)  # Dodge
    with _deck(["8 of spades"]):
        state, lines = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["player"]["hp"] == 11  # evaded
    assert any("avoid" in line.lower() for line in lines)


def test_arcane_shield_reduces_next_attack():
    char = _char(legacy="seer")
    state = _start(char, hand=["2 of hearts", "3 of hearts", "4 of clubs", "5 of clubs"])
    state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck(["8 of spades"]):
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["player"]["hp"] == 15 - 2


def test_charging_assault_costs_your_next_turn():
    char = _char()
    state = _start(char, init=("2 of hearts", "king of clubs"))
    with _deck(["3 of spades"]):
        state, lines = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["player"]["hp"] == 12
    assert state["turn"] == "opponent"  # your turn was lost
    assert len(state["tactic_hand"]) == 4
    assert any("lose this turn" in line.lower() for line in lines)


def test_stunned_opponent_draws_no_card_and_no_extra_buffs():
    char = _char()
    state = _start(char, hand=["5 of hearts", "3 of hearts", "4 of clubs", "6 of clubs"])
    state, _ = combat_action(
        state, char, "play_tactic", char_id="c1", hand_index=0
    )  # Stunning Blow
    with patch(MANAGER) as draw:
        state, lines = combat_action(state, char, "opponent_turn", char_id="c1")
        draw.assert_not_called()
    assert any("loses its turn" in line for line in lines)
    assert not any("Aerith" in line for line in lines)


def test_morale_zero_is_defeat():
    char = _char(morale=3)
    state = _start(char, init=("2 of hearts", "king of clubs"))
    with _deck(["7 of spades"]):  # Terrifying Howl: Morale -3
        state, lines = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["status"] == "lost"
    assert state["defeat_stat"] == "morale"


def test_health_zero_is_defeat_not_fallback_to_old_health():
    """Bug: ``hp or char.health`` kept the old Health when hp hit 0."""
    char = _char(health=4)
    state = _start(char, init=("2 of hearts", "king of clubs"))
    with _deck(["8 of spades"]):
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["status"] == "lost"
    assert char.health == 0


def test_out_of_cards_offers_new_round_or_retreat():
    char = _char()
    state = _start(char, hand=["3 of hearts"] * 1 + ["3 of clubs"] * 0)
    state["tactic_hand"] = ["3 of hearts"]
    state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck(["2 of spades"]):
        state, lines = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["needs_new_round"] is True
    with pytest.raises(ValueError):
        combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck(["4 of hearts", "5 of hearts", "6 of hearts", "7 of hearts"]):
        state, lines = combat_action(state, char, "new_round", char_id="c1")
    assert len(state["tactic_hand"]) == 4 and state["round"] == 2
    state["tactic_hand"] = []
    state["needs_new_round"] = True
    state, _ = combat_action(state, char, "retreat", char_id="c1")
    assert state["status"] == "retreated"


def test_red_table_win_flags_item_reward():
    char = _char()
    state = _start(char, ctx_card="jack of hearts")
    assert state["red_table"] is True
    state["opponent"]["hp"] = 1
    state, lines = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["status"] == "won"
    assert state["reward_item"] is True


def test_black_table_win_has_no_item():
    char = _char()
    state = _start(char, ctx_card="jack of clubs")
    state["opponent"]["hp"] = 1
    state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["status"] == "won"
    assert not state.get("reward_item")


def test_roar_of_defiance_halves_next_attack_rounded_up():
    state = {"opponent": {"label": "Wolf", "hp": 12, "max_hp": 12}, "player": {"hp": 10}}
    apply_tactic_effects(state, {"label": "Roar", "opponent_halve_next": 1}, actor="opponent")
    apply_tactic_effects(state, {"label": "Hit", "damage": 5}, actor="player")
    assert state["opponent"]["hp"] == 12 - 3


def test_pack_attack_secondary_opponent_hits_each_turn():
    state = {"opponent": {"label": "Wolf", "hp": 12, "max_hp": 12}, "player": {"hp": 10}}
    apply_tactic_effects(
        state, {"label": "Pack", "summon_hp": 3, "summon_damage": 2}, actor="opponent"
    )
    from backend.games.brambletrek.combat.effects import resolve_opponent_turn_effects

    resolve_opponent_turn_effects(state, skipped=False)
    assert state["player"]["hp"] == 8


def test_magic_missile_ticks_on_opponent_turns():
    char = _char(legacy="seer")
    state = _start(char, hand=["9 of hearts", "3 of hearts", "4 of clubs", "5 of clubs"])
    hp0 = state["opponent"]["hp"]
    state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck(["2 of spades"]):
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["opponent"]["hp"] == hp0 - 3


def test_combat_route_lost_triggers_health_recovery(isolated_saves, monkeypatch):
    from backend.games.brambletrek import play_handlers
    from backend.games.brambletrek.combat.state import COMBAT_STATE_KEY
    from backend.storage import create_session, save_character, update_session_extras

    save_character(
        "bt1",
        {
            "id": "bt1",
            "game_id": "brambletrek",
            "name": "B",
            "legacy": "scrapper",
            "health": 3,
            "morale": 10,
            "supplies": 10,
        },
    )
    sid = create_session(character_id="bt1", adventure_id="")
    char = play_handlers._char("bt1")
    state = _start(char, init=("2 of hearts", "king of clubs"))
    update_session_extras(sid, {COMBAT_STATE_KEY: state})
    with _deck(["8 of spades"]):
        out = play_handlers.session_combat_action(sid, "bt1", "opponent_turn")
    assert out["combat"]["status"] == "lost"
    assert out["character"]["health"] == 10  # half of max 20, rounded up (p. 16)
    assert out["combat"]["recovery"][0]["stat"] == "health"


def test_player_dot_ticks_on_following_opponent_turns():
    from backend.games.brambletrek.combat.effects import (
        apply_tactic_effects,
        resolve_opponent_turn_effects,
    )

    state = {"opponent": {"label": "Crab", "hp": 12, "max_hp": 12}, "player": {"hp": 10}}
    apply_tactic_effects(
        state,
        {"label": "Dangerous Waters", "player_dot_damage": 2, "player_dot_turns": 3},
        actor="opponent",
    )
    assert state["player"]["hp"] == 10
    # Same opponent turn as the tactic: DoT is armed but does not tick yet.
    resolve_opponent_turn_effects(state, skipped=False)
    assert state["player"]["hp"] == 10
    resolve_opponent_turn_effects(state, skipped=False)
    assert state["player"]["hp"] == 8
    resolve_opponent_turn_effects(state, skipped=False)
    assert state["player"]["hp"] == 6
    resolve_opponent_turn_effects(state, skipped=False)
    assert state["player"]["hp"] == 4
    resolve_opponent_turn_effects(state, skipped=False)
    assert state["player"]["hp"] == 4


def test_skip_turns_counts_two_player_turns():
    from backend.games.brambletrek.combat.effects import apply_tactic_effects

    state = {
        "opponent": {"label": "Sprite", "hp": 8, "max_hp": 8},
        "player": {"hp": 10},
        "buffs": {},
    }
    apply_tactic_effects(
        state,
        {"label": "Enchanted Whirl", "damage": 3, "skip_turn": True, "skip_turns": 2},
        actor="opponent",
    )
    assert state["player"]["hp"] == 7
    assert int((state.get("buffs") or {}).get("skip_player") or 0) == 2


def test_molten_golem_regeneration_is_hot():
    from backend.games.brambletrek.modules.combat import lookup_opponent_tactic

    tactic = lookup_opponent_tactic("dragonkeep", "molten_golem", "queen of spades")
    assert tactic and tactic.get("heal_per_turn") == 2 and tactic.get("heal_per_turn_turns") == 3
