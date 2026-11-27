"""Journey day from the play view: deterministic draws, DEPTHS, Journey panel, combat start."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.games.brambletrek.dm.curated import journey_depths_trace, order_depths_last

TESTER_DRAW = ["4 of hearts", "10 of spades", "8 of diamonds", "8 of clubs"]


def _setup(isolated_saves):
    from backend.storage import create_session, save_character

    save_character(
        "qa2",
        {
            "id": "qa2",
            "game_id": "brambletrek",
            "name": "QA Bramble 2",
            "legacy": "seer",
            "health": 10,
            "morale": 18,
            "supplies": 20,
        },
    )
    return create_session(character_id="qa2", adventure_id="")


def _journey_shortcut(sid, cards=TESTER_DRAW):
    from backend.routes import sessions as routes

    fake = {"ok": True, "cards": list(cards), "remaining": 48}
    with patch("backend.games.brambletrek.actions.draw_cards", return_value=fake):
        return routes._execute_shortcut(
            sid, routes.ShortcutBody(shortcut_id="journey_day", params={})
        )


def test_first_depths_card_ends_the_day():
    order, set_aside = order_depths_last(TESTER_DRAW, start_in_aldwund=False)
    # 10♠, 8♦ and 8♣ are all (DEPTHS): the first one drawn is the day's last event.
    assert order == ["4 of hearts", "10 of spades"]
    assert set_aside == ["8 of diamonds", "8 of clubs"]
    assert journey_depths_trace(order, start_in_aldwund=False) == [False, False]


def test_depths_order_unchanged_in_aldwund():
    assert order_depths_last(TESTER_DRAW, start_in_aldwund=True) == (TESTER_DRAW, [])


def test_journey_shortcut_stashes_pending_journey_and_is_deterministic(isolated_saves):
    from backend.games.brambletrek.play_handlers import pending_journey_payload

    sid = _setup(isolated_saves)
    result = _journey_shortcut(sid)
    assert result["task"] == "journey"
    assert result["journey_cards"] == ["4 of hearts", "10 of spades"]
    assert "ends the day" in result["user_message"]
    pending = pending_journey_payload(sid, "qa2")
    assert pending and [e["card"] for e in pending["events"]] == result["journey_cards"]


def test_apply_events_change_the_sheet_and_finish_day(isolated_saves):
    from backend.games.brambletrek import play_handlers
    from backend.storage import get_character

    sid = _setup(isolated_saves)
    _journey_shortcut(sid)
    play_handlers.apply_journey_event(sid, "qa2", 0)
    play_handlers.apply_journey_event(sid, "qa2", 1)
    char = get_character("qa2")
    assert char["morale"] == 8  # 18 - 10 (Cave home to a beast)
    assert char["in_aldwund"] is True
    out = play_handlers.finish_journey_day(sid, "qa2")
    assert out["character"]["journey_day"] >= 2


def test_finish_day_rejects_unapplied_events(isolated_saves):
    from backend.games.brambletrek import play_handlers

    sid = _setup(isolated_saves)
    _journey_shortcut(sid, cards=["2 of spades", "3 of spades", "9 of clubs", "ace of spades"])
    play_handlers.apply_journey_event(sid, "qa2", 0)
    play_handlers.apply_journey_event(sid, "qa2", 1)
    play_handlers.apply_journey_event(sid, "qa2", 2)
    with pytest.raises(ValueError, match="Resolve all journey events"):
        play_handlers.finish_journey_day(sid, "qa2")
    play_handlers.apply_journey_event(sid, "qa2", 3)
    out = play_handlers.finish_journey_day(sid, "qa2")
    assert out["pending_journey"] is None


def test_journey_turn_skips_rag_and_answers_with_next_steps():
    from backend.games.brambletrek.dm import pipeline
    from backend.games.brambletrek.dm.agents import nodes

    shortcut = {"task": "journey", "summary": "Open the **Journey** panel", "user_message": "x"}
    state = {"shortcut_result": shortcut, "mechanics_summary": "x", "user_message": "x"}
    with patch.object(nodes, "query_rules", side_effect=AssertionError("no RAG")):
        assert nodes.rules_facilitator_node(state) == {"rules_context": "", "rules_sources": []}
    assert pipeline.resolve_response_node(state)["response"] == "Open the **Journey** panel"


def test_manual_combat_start(isolated_saves):
    from backend.games.brambletrek import play_handlers

    sid = _setup(isolated_saves)
    with pytest.raises(ValueError):
        play_handlers.start_manual_combat(sid, "qa2", "7", "clubs")
    seq = [
        {"ok": True, "cards": ["2 of hearts", "king of clubs"], "remaining": 50},
        {"ok": True, "cards": ["3 of hearts", "4 of hearts", "5 of hearts", "6 of hearts"],
         "remaining": 46},
    ]  # fmt: skip
    with patch("backend.games.brambletrek.combat.manager.draw_cards", side_effect=seq):
        out = play_handlers.start_manual_combat(sid, "qa2", "queen", "hearts")
    assert out["combat"]["status"] == "active"
    assert out["combat"]["opponent"]["hp"] == 12
    with pytest.raises(ValueError):
        play_handlers.start_manual_combat(sid, "qa2", "jack", "clubs")


def test_dragonkeep_endpoint_is_quiet_for_other_adventures(isolated_saves):
    from backend.routes import brambletrek as routes

    sid = _setup(isolated_saves)
    assert routes.get_dragonkeep(sid)["dragonkeep"] is None


def test_lore_draws_unique_prophecy_fragment(isolated_saves):
    from backend.games.brambletrek import play_handlers

    extras: dict = {"brambletrek_lore_found": ["2"]}
    seq = [
        {"ok": True, "cards": ["2 of clubs"], "remaining": 40},
        {"ok": True, "cards": ["3 of clubs"], "remaining": 39},
    ]
    with patch.object(play_handlers, "draw_cards", side_effect=seq):
        lore = play_handlers._draw_lore_fragment("s", "c", extras, "world_tree")
    assert lore["card"] == "3 of clubs" and lore["text"].startswith('"In groves sacred')
    assert extras["brambletrek_lore_found"] == ["2", "3"]


def test_module_legacies_selectable_but_not_rolled():
    from backend.games.brambletrek.characters.entity import get_legacy_options
    from backend.games.brambletrek.dm.curated import legacy_id_by_roll

    opts = get_legacy_options()
    assert "snacker" in opts and "surveyor" in opts
    assert {legacy_id_by_roll(i) for i in range(1, 13)} == {
        "seer", "scrapper", "storyteller", "seeker", "sneaker", "soother"
    }  # fmt: skip


def test_dm_headings_are_not_npcs():
    from backend.dm.session_world import extract_marked_names

    text = (
        "**Day Summary**\n- **Precious Minerals** (+2 Morale)\n**Reminders**:\n"
        "**Supplies Recovery Table**\nYou meet **Mira Thornfoot** at the gate."
    )
    assert extract_marked_names(text) == ["Mira Thornfoot"]


def test_ui_labels_are_not_npcs():
    from backend.dm.memory_dedupe import looks_like_entity_name
    from backend.dm.session_world import extract_marked_names

    for label in ("Apply", "Combat", "Finish day", "Start combat", "Journey", "Deck"):
        assert looks_like_entity_name(label) is False, label
    assert looks_like_entity_name("Mira Thornfoot") is True
    text = (
        "Drew 2 card(s). Open the **Journey** panel: **Apply** each event in order, "
        "start **Combat** on face cards, then **Finish day**."
    )
    assert extract_marked_names(text) == []


def test_zero_stats_restore_on_the_following_day_and_cost_one_day(isolated_saves):
    """Core Rulebook p. 16: recovery is checked after today's events, not mid-apply.

    Restore to half of max (rounded up) happens on the following day, which is
    lost (no event cards). Several resources still at 0 cost one day total.
    Sequence from the QA session starting Day 2, HP 8, Morale 11, Supplies 13.
    """
    from backend.games.brambletrek import play_handlers
    from backend.storage import create_session, get_character, save_character

    save_character(
        "qa2",
        {
            "id": "qa2",
            "game_id": "brambletrek",
            "name": "QA Bramble 2",
            "legacy": "seer",
            "health": 8,
            "morale": 11,
            "supplies": 13,
            "journey_day": 2,
        },
    )
    sid = create_session(character_id="qa2", adventure_id="")
    cards = ["9 of clubs", "ace of clubs", "7 of spades", "8 of diamonds"]
    result = _journey_shortcut(sid, cards=cards)
    assert result["journey_cards"] == cards

    item = {"ok": True, "cards": ["2 of clubs"], "remaining": 40}
    rec_draws = [
        {"ok": True, "cards": [c], "remaining": n}
        for n, c in ((39, "jack of diamonds"), (38, "4 of diamonds"), (37, "9 of spades"))
    ]
    # Item draw goes through play_handlers.draw_cards; recovery through recovery.draw_cards.
    with (
        patch("backend.games.brambletrek.play_handlers.draw_cards", return_value=item),
        patch("backend.games.brambletrek.recovery.draw_cards", side_effect=rec_draws),
    ):
        after = [play_handlers.apply_journey_event(sid, "qa2", i) for i in range(4)]

    char = get_character("qa2")
    # Mid-day: no half-max restore. 8-9→0, all-10 stays 0 / M 1 / S 3,
    # then M-3 & S-3 → 0, 8♦ Supplies +8, pebble +1 Health.
    assert (char["health"], char["morale"], char["supplies"]) == (1, 0, 8)
    assert char["in_aldwund"] is True
    assert char["journey_day"] == 2
    # Only stats still at 0 after all events need recovery (Health and Supplies recovered).
    assert after[-1]["pending_recoveries"] == ["morale"]
    # Must not have already skipped a day or restored to 10 mid-apply.
    assert all(not ev.get("recoveries") for ev in after)

    with patch(
        "backend.games.brambletrek.recovery.draw_cards",
        side_effect=rec_draws,
    ):
        out = play_handlers.finish_journey_day(sid, "qa2")
    char = get_character("qa2")
    # Rest first (p. 15): -4 Supplies, +2 Health → HP 3, S 4.
    # Recovery day (p. 16): only Morale (still 0) to half of 20, rounded up (10).
    # One lost day + the normal +1: Day 2 → 4.
    assert out["lost_day"] is True
    assert (char["health"], char["morale"], char["supplies"]) == (3, 10, 4)
    assert char["journey_day"] == 4


def test_mid_day_zero_then_heal_skips_recovery(isolated_saves):
    from backend.games.brambletrek import play_handlers
    from backend.storage import create_session, get_character, save_character

    save_character(
        "qa2",
        {
            "id": "qa2",
            "game_id": "brambletrek",
            "name": "QA Bramble 2",
            "legacy": "seer",
            "health": 10,
            "morale": 4,
            "supplies": 10,
            "journey_day": 3,
        },
    )
    sid = create_session(character_id="qa2", adventure_id="")
    cards = ["9 of spades", "5 of diamonds"]
    _journey_shortcut(sid, cards=cards)
    after0 = play_handlers.apply_journey_event(sid, "qa2", 0)
    assert after0["pending_recoveries"] == ["morale"]
    after1 = play_handlers.apply_journey_event(sid, "qa2", 1)
    assert after1["pending_recoveries"] == []
    char = get_character("qa2")
    assert (char["health"], char["morale"], char["supplies"]) == (10, 5, 10)
    out = play_handlers.finish_journey_day(sid, "qa2")
    assert out["lost_day"] is False
    char = get_character("qa2")
    assert (char["health"], char["morale"], char["supplies"]) == (12, 5, 6)
    assert char["journey_day"] == 4
