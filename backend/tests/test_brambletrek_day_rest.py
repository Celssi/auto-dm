"""End-of-day rest, Recovery Tables and deck persistence (Core Rulebook pp. 8, 15-16)."""

from __future__ import annotations

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.recovery import resolve_zero_resources, rest_at_day_end


def test_rest_spends_four_supplies_for_two_health(isolated_saves):
    char = BrambletrekCharacter(name="R", health=10, morale=10, supplies=9)
    out = rest_at_day_end(char, char_id="r1")
    assert out["rested"] is True
    assert (char.health, char.supplies) == (12, 5)


def test_rest_with_fewer_than_four_supplies_draws_supplies_recovery(isolated_saves):
    char = BrambletrekCharacter(name="R", health=10, morale=10, supplies=3)
    out = rest_at_day_end(char, char_id="r1")
    assert out["rested"] is False
    assert char.health == 10
    assert char.supplies == 10  # half of max 20 (p. 16)
    assert out["recoveries"][0]["stat"] == "supplies"


def test_zero_resource_triggers_recovery(isolated_saves):
    char = BrambletrekCharacter(name="R", health=8, morale=0, supplies=8)
    recs = resolve_zero_resources(char, char_id="r1")
    assert [r["stat"] for r in recs] == ["morale"]
    assert char.morale == 10
    assert recs[0]["label"]


def test_finish_day_rests_reshuffles_and_skips_recovery_day(isolated_saves):
    from backend.games.brambletrek import play_handlers
    from backend.play_tools import deck_remaining, draw_cards
    from backend.storage import create_session, get_character, save_character

    save_character(
        "d1",
        {
            "id": "d1",
            "game_id": "brambletrek",
            "name": "D",
            "legacy": "seer",
            "health": 10,
            "morale": 10,
            "supplies": 4,
            "journey_day": 1,
        },
    )
    sid = create_session(character_id="d1", adventure_id="")
    draw_cards(10, game_id="brambletrek", char_id="d1")
    out = play_handlers.finish_journey_day(sid, "d1")
    char = get_character("d1")
    # 4 Supplies paid for +2 Health; Supplies hit 0 -> Supplies Recovery -> the next day is lost.
    assert char["health"] == 12
    assert char["supplies"] == 10
    assert out["lost_day"] is True
    assert char["journey_day"] == 3
    assert deck_remaining("brambletrek", "d1") == 52  # reshuffled for the new day
    out = play_handlers.finish_journey_day(sid, "d1")
    char = get_character("d1")
    assert out["lost_day"] is False
    assert (char["health"], char["supplies"], char["journey_day"]) == (14, 6, 4)


def test_deck_state_survives_process_cache_loss(isolated_saves):
    from backend.play_tools import clear_deck_store, deck_remaining, draw_cards

    first = draw_cards(5, game_id="brambletrek", char_id="p1")
    assert first["ok"] and first["remaining"] == 47
    clear_deck_store()  # simulate a new Cloud Run instance
    assert deck_remaining("brambletrek", "p1") == 47
    again = draw_cards(1, game_id="brambletrek", char_id="p1")
    assert again["cards"][0] not in first["cards"]


def test_draw_error_key_present():
    from backend.play_tools import draw_cards

    out = draw_cards(0, game_id="brambletrek", char_id="x")
    assert out["ok"] is False and out["error"]
