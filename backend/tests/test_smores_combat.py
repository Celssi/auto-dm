"""Smores ally in Frozen Forest combat (CDE printed pp. 110–111)."""

from __future__ import annotations

from unittest.mock import patch

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.effects import apply_tactic_effects, half_up
from backend.games.brambletrek.combat.manager import begin_combat, combat_action, combat_payload
from backend.games.brambletrek.combat.smores import lookup_smores_tactic
from backend.games.brambletrek.modules.loader import load_module

MANAGER = "backend.games.brambletrek.combat.manager.draw_cards"


def _char(**kw) -> BrambletrekCharacter:
    c = BrambletrekCharacter(
        name="T",
        legacy="scrapper",
        health=12,
        morale=8,
        supplies=10,
        active_adventure="first_frost",
    )
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def _deck(*draws: list[str]):
    seq = [{"ok": True, "cards": list(d), "remaining": 40} for d in draws]
    return patch(MANAGER, side_effect=seq)


def _ctx(**extra):
    return {
        "adventure_id": "first_frost",
        "type": "core",
        "card": "jack of clubs",
        "ally": "smores",
        **extra,
    }


def _start(*, first_player=True, smores_hand=None, daily_used=""):
    smores_hand = smores_hand or ["4 of hearts", "8 of clubs", "queen of spades", "ace of diamonds"]
    init = ("10 of hearts", "2 of clubs") if first_player else ("2 of hearts", "king of clubs")
    player_hand = ["3 of hearts", "5 of hearts", "6 of hearts", "7 of hearts"]
    with _deck(list(init), player_hand, smores_hand):
        return begin_combat(_char(), _ctx(smores_daily_used=daily_used), char_id="c1")


def test_smores_tactics_table_is_complete():
    table = (load_module("first_frost").get("scene_tables") or {}).get("smores_tactics") or {}
    for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace"):
        row = lookup_smores_tactic(f"{rank} of hearts")
        assert row and rank in table
        assert row.get("label")
    queen = lookup_smores_tactic("queen of hearts")
    assert queen and queen.get("halve_opponent_damage_round") == "down"
    ace = lookup_smores_tactic("ace of hearts")
    assert ace and ace.get("damage_formula") == "draw_half_up"


def test_smores_joins_after_the_player_when_you_win_initiative():
    state = _start(first_player=True)
    assert state["ally"]["id"] == "smores"
    assert len(state["ally"]["hand"]) == 4
    assert state["turn"] == "player"
    payload = combat_payload(state)
    assert payload and payload["ally"]["label"] == "Smores"

    char = _char()
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "smores"


def test_smores_follows_you_even_when_the_opponent_starts():
    state = _start(first_player=False)
    assert state["turn"] == "opponent"
    char = _char()
    with _deck(["2 of clubs"]):
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["turn"] == "player"
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "smores"


def test_celebration_combat_has_no_smores():
    ctx = {"adventure_id": "first_frost", "type": "core", "card": "jack of clubs"}
    with _deck(
        ["10 of hearts", "2 of clubs"],
        ["3 of hearts", "4 of hearts", "5 of hearts", "6 of hearts"],
    ):
        state = begin_combat(_char(), ctx, char_id="c1")
    assert not state.get("ally")
    char = _char()
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "opponent"


def test_sweet_roll_deals_three_and_quiet_quell_halves_rounded_down():
    state = _start(smores_hand=["4 of hearts", "queen of clubs", "2 of spades", "3 of spades"])
    char = _char()
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "smores"
    hp0 = state["opponent"]["hp"]
    with _deck():
        state, lines = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    assert state["opponent"]["hp"] == hp0 - 3
    assert state["turn"] == "opponent"

    # Play Quiet Quell on the next Smores turn, then a 5-damage opponent hit becomes 2.
    with _deck(["king of clubs"]):  # opponent 5? depends on core table; force via effects
        state, _ = combat_action(state, char, "opponent_turn", char_id="c1")
    assert state["turn"] == "player"
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck():
        state, _ = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    # Queen is now at index 0 after the 4 was played earlier... wait we already popped 4,
    # hand starts [4, Q, 2, 3], first play popped 4, hand [Q, 2, 3], this play is Queen.
    player_hp = state["player"]["hp"]
    apply_tactic_effects(state, {"label": "hit", "damage": 5}, actor="opponent")
    # 5 // 2 = 2 (rounded-down)
    assert state["player"]["hp"] == player_hp - 2


def test_sticky_ambush_draw_half_up():
    # Ace=11, half rounded up is 6 (p. 8 / Smores Ace text).
    assert half_up(11) == 6
    state = _start(smores_hand=["ace of hearts", "2 of clubs", "3 of clubs", "4 of clubs"])
    char = _char()
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    hp0 = state["opponent"]["hp"]
    with _deck(["ace of spades"]):
        state, lines = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    assert state["opponent"]["hp"] == hp0 - 6
    assert any("rounded up" in line.lower() for line in lines)


def test_spike_flurry_miss_chance_is_fifty_percent():
    state = _start()
    apply_tactic_effects(
        state,
        lookup_smores_tactic("7 of hearts"),
        actor="smores",
    )
    hp = state["player"]["hp"]
    state["next_chance_roll"] = 0  # miss
    apply_tactic_effects(state, {"label": "Bite", "damage": 4}, actor="opponent")
    assert state["player"]["hp"] == hp
    state["next_chance_roll"] = 90  # hit
    apply_tactic_effects(state, {"label": "Bite", "damage": 4}, actor="opponent")
    assert state["player"]["hp"] == hp - 4


def test_shield_reduces_player_damage_and_blocks_sweet_treat_same_day():
    state = _start()
    char = _char()
    state, lines = combat_action(state, char, "smores_shield", char_id="c1")
    assert "Shield" in " ".join(lines)
    hp = state["player"]["hp"]
    apply_tactic_effects(state, {"label": "Bite", "damage": 5}, actor="opponent")
    assert state["player"]["hp"] == hp - 2
    try:
        combat_action(state, char, "smores_sweet_treat", char_id="c1")
        raise AssertionError("expected daily already used")
    except ValueError as exc:
        assert "already used" in str(exc)


def test_intercept_uses_temp_hp_and_overflow_hits_the_player():
    state = _start(smores_hand=["10 of hearts", "2 of clubs", "3 of clubs", "4 of clubs"])
    char = _char()
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck():
        state, _ = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    assert state["ally"]["temp_hp"] == 4
    state, _ = combat_action(state, char, "smores_intercept", char_id="c1")
    assert state["ally"]["intercept_next"] is True
    player_hp = state["player"]["hp"]
    apply_tactic_effects(state, {"label": "Bite", "damage": 6}, actor="opponent")
    assert state["ally"]["temp_hp"] == 0
    # 4 soaked, 2 overflow to the player (no book HP for Smores)
    assert state["player"]["hp"] == player_hp - 2


def test_sugar_rush_gives_smores_two_extra_actions():
    state = _start(smores_hand=["8 of hearts", "4 of clubs", "2 of clubs", "3 of clubs"])
    char = _char()
    with _deck():
        state, _ = combat_action(state, char, "play_tactic", char_id="c1", hand_index=0)
    with _deck():
        state, lines = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "smores"
    assert any("another action" in line.lower() for line in lines)
    with _deck():
        state, _ = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "smores"
    with _deck():
        state, _ = combat_action(state, char, "play_smores_tactic", char_id="c1", hand_index=0)
    assert state["turn"] == "opponent"


def test_sweet_treat_heals_and_resets_after_finish_day(isolated_saves):
    from backend.games.brambletrek import play_handlers
    from backend.storage import create_session, save_character, update_session_extras

    save_character(
        "bt-smores",
        {
            "id": "bt-smores",
            "game_id": "brambletrek",
            "name": "B",
            "legacy": "scrapper",
            "health": 8,
            "morale": 6,
            "supplies": 12,
            "active_adventure": "first_frost",
        },
    )
    sid = create_session(character_id="bt-smores", adventure_id="first_frost")
    update_session_extras(
        sid,
        {
            play_handlers.FIRST_FROST_PHASE_KEY: "frozen_forest",
        },
    )
    # Start via helper context
    char = play_handlers._char("bt-smores")
    extras = play_handlers._session_extras(sid)
    ctx = play_handlers._with_smores_context(
        extras,
        "first_frost",
        {"adventure_id": "first_frost", "type": "core", "card": "jack of clubs"},
    )
    with _deck(
        ["10 of hearts", "2 of clubs"],
        ["3 of hearts", "4 of hearts", "5 of hearts", "6 of hearts"],
        ["2 of clubs", "3 of clubs", "4 of clubs", "5 of clubs"],
    ):
        state = begin_combat(char, ctx, char_id="bt-smores")
    extras[play_handlers.COMBAT_STATE_KEY] = state
    play_handlers._set_extras(sid, extras)
    out = play_handlers.session_combat_action(sid, "bt-smores", "smores_sweet_treat")
    assert out["character"]["health"] == 10
    assert out["character"]["morale"] == 7
    extras = play_handlers._session_extras(sid)
    assert extras[play_handlers.SMORES_DAILY_KEY] == "sweet_treat"
    play_handlers.finish_journey_day(sid, "bt-smores")
    extras = play_handlers._session_extras(sid)
    assert not extras.get(play_handlers.SMORES_DAILY_KEY)
