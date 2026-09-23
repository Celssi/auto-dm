"""Tests for Dragonkeep session phase state."""

from backend.games.brambletrek.modules.dragonkeep_state import (
    DRAGONKEEP_STATE_KEY,
    advance_finale,
    advance_finale_phase,
    advance_path,
    choose_gem,
    complete_exploration,
    default_state,
    dragonkeep_payload,
    ensure_dragonkeep_state,
    open_door,
    set_combat_from_exploration,
    to_antechamber,
    to_door,
)


def test_default_path_phase():
    state = default_state()
    payload = dragonkeep_payload(state)
    assert payload["phase"] == "path"
    assert payload["path_step"] == 1
    assert "advance_path" in payload["actions"] or "draw_path" in payload["actions"]


def test_path_draw_and_advance():
    state = default_state()
    state["path_step"] = 2
    # suit outcomes at step 2 — mock outcome without deck
    state["pending_path_outcome"] = {"label": "Backpack", "supplies": 3}
    state["path_resolved"] = True
    advance_path(state)
    assert state["path_step"] == 3


def test_path_to_labyrinth():
    state = default_state()
    state["path_step"] = 7
    state["path_resolved"] = True
    advance_path(state)
    assert state["phase"] == "labyrinth"


def test_gem_exploration_cycle():
    state = default_state()
    state["phase"] = "gems"
    choose_gem(state, "path_of_tempest")
    assert state["phase"] == "exploration"
    assert state["active_gem"] == "path_of_tempest"
    complete_exploration(state)
    assert state["phase"] == "gems"
    assert "path_of_tempest" in state["gems_completed"]


def test_antechamber_requires_gem():
    state = default_state()
    state["phase"] = "gems"
    try:
        to_antechamber(state)
        assert False, "should require completed gem"
    except ValueError:
        pass
    state["gems_completed"] = ["path_of_tempest"]
    to_antechamber(state)
    assert state["phase"] == "antechamber"
    assert state["met_eolan"]


def test_ensure_dragonkeep_state_in_extras():
    extras: dict = {}
    state = ensure_dragonkeep_state(extras)
    assert DRAGONKEEP_STATE_KEY in extras
    assert state["phase"] == "path"


def test_finale_flow():
    state = default_state()
    state["phase"] = "gems"
    state["gems_completed"] = ["path_of_tempest"]
    to_antechamber(state)
    assert state["finale_step"] == "meet"
    to_door(state)
    assert state["phase"] == "door"
    try:
        open_door(state, oracle_relic=False)
        assert False, "should require oracle relic"
    except ValueError as e:
        assert "Oracle" in str(e)
    open_door(state, oracle_relic=True)
    assert state["phase"] == "finale"
    assert state["finale_step"] == "chambers"
    advance_finale(state)
    assert state["finale_step"] == "dragon"
    assert state["combat_context"]["finale"] is True
    advance_finale_phase(state)
    assert state["finale_phase"] == "2"


def test_exploration_combat_context():
    state = default_state()
    state["phase"] = "exploration"
    state["active_gem"] = "path_of_tempest"
    ctx = set_combat_from_exploration(
        state,
        gem_path="path_of_tempest",
        event_card="jack of hearts",
    )
    assert ctx["opponent_id"] == "water_elemental"
    assert state["combat_context"]["event_card"] == "jack of hearts"
