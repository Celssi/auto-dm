"""Brambletrek chat/session fixes: player-mode free text, shortcut settings, live keys."""

from __future__ import annotations

from unittest.mock import patch

from backend.dm.state import game_plugin
from backend.games.brambletrek.dm.agents import nodes
from backend.storage import LIVE_CHARACTER_KEYS

NODES = "backend.games.brambletrek.dm.agents.nodes"


def _session(mode: str):
    return patch(f"{NODES}.get_session", return_value={"extras": {"story_mode": mode}})


def test_free_text_needs_rules_and_runs_facilitator_in_player_mode():
    state = {
        "user_message": "I inspect the moss near camp",
        "character": {"game_id": "brambletrek"},
    }
    updates = nodes.router_node(state)
    assert updates["needs_rules"] is True
    with _session("player"):
        assert nodes._should_run_facilitator({**state, **updates}) is True


def test_player_mode_shortcut_answer_skips_facilitator():
    state = {
        "user_message": "/day",
        "response": "Day 2: you drew 3 cards.",
        "shortcut_result": {"task": "journey_day"},
    }
    with _session("player"):
        assert nodes._should_run_facilitator(state) is False


def test_player_mode_free_text_reply_is_not_empty():
    state = {
        "session_id": "s1",
        "user_message": "How does resting work?",
        "character": {"game_id": "brambletrek", "name": "Pip"},
        "needs_rules": True,
    }
    with (
        _session("player"),
        patch(f"{NODES}.narration_enabled", return_value=False),
        patch(f"{NODES}.get_langchain_chat_llm", return_value=object()),
        patch(f"{NODES}.invoke_chat_llm", return_value="Resting costs 4 Supplies."),
        patch(f"{NODES}.message_text", side_effect=lambda r: r),
    ):
        out = nodes.facilitator_node(state)
    assert out["response"] == "Resting costs 4 Supplies."


def test_brambletrek_skips_dnd_story_director():
    assert game_plugin({"game_id": "brambletrek"}).play.skip_story_director is True
    assert game_plugin({"game_id": "dnd5e"}).play.skip_story_director is False


def test_brambletrek_resources_are_live_keys():
    for key in ("health", "morale", "supplies", "journey_day"):
        assert key in LIVE_CHARACTER_KEYS


def test_shortcut_route_passes_session_card_source():
    from backend.routes import sessions as routes

    captured = {}

    class Play:
        @staticmethod
        def on_shortcut_result(*_args):
            return None

    class Plugin:
        play = Play()

        def run_shortcut(self, shortcut_id, **params):
            captured.update(params)
            return {"summary": "ok"}

    sess = {"character_id": "c1", "extras": {"card_source": "physical", "story_mode": "player"}}
    with (
        patch.object(routes, "get_session", return_value=sess),
        patch.object(routes, "get_character", return_value={"game_id": "brambletrek"}),
        patch.object(routes, "get_game", return_value=Plugin()),
        patch(
            "backend.games.brambletrek.play_handlers.get_session_combat_context",
            return_value=None,
        ),
    ):
        routes._execute_shortcut("s1", routes.ShortcutBody(shortcut_id="journey_day", params={}))
    assert captured["card_source"] == "physical"
