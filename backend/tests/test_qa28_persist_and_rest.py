"""QA of persist races, rest HD, Bless slots, lonelog, and audit. Mocked LLM, no live Anthropic."""

from __future__ import annotations

from unittest.mock import patch

from backend.dm.audit import format_audit_summary, read_audit_events
from backend.dm.trace import dm_turn_trace
from backend.games.dnd5e.dm.mechanics_delta import apply_mechanics_delta
from backend.games.dnd5e.dm.resource_keeper import apply_pending_rest
from backend.storage import (
    append_session_log,
    get_character,
    get_session,
    get_session_lonelog,
    persist_shown_reply,
    persist_user_message,
    save_character,
    save_session_messages,
)


def _paladin(**overrides):
    data = {
        "id": "persist-paladin",
        "name": "QA Paladin",
        "game_id": "dnd5e",
        "species": "human",
        "class_name": "paladin",
        "level": 1,
        "hp": 8,
        "max_hp": 12,
        "ac": 18,
        "hit_die": 10,
        "hit_dice_max": 1,
        "hit_dice_spent": 0,
        "lay_on_hands_remaining": 0,
        "heroic_inspiration": False,
        "conditions": [],
        "active_effects": [],
        "concentration": "",
        "spell_slots": {"1": 2},
        "prepared_spells": ["Bless", "Cure Wounds"],
        "classes": [{"class_name": "paladin", "level": 1}],
        "ability_scores": {"str": 16, "dex": 10, "con": 14, "int": 8, "wis": 10, "cha": 15},
    }
    data.update(overrides)
    return data


def _session(isolated_saves, char: dict | None = None) -> tuple[str, str]:
    from backend import storage

    _ = isolated_saves
    row = char or _paladin()
    cid = save_character(row.get("id") or "persist-paladin", row)
    adv = storage.save_adventure(None, {"name": "QA persist", "character_id": cid})
    sid = storage.create_session(character_id=cid, adventure_id=adv, name="QA persist")
    return sid, cid


def test_stale_character_snapshot_does_not_revert_live_fields(isolated_saves):
    sid, cid = _session(isolated_saves, _paladin(hp=8, lay_on_hands_remaining=0, spell_slots={"1": 1}))
    _ = sid
    rested = get_character(cid)
    rested.update({"hp": 12, "lay_on_hands_remaining": 5, "spell_slots": {"1": 2}})
    save_character(cid, rested)
    current = get_character(cid)
    assert current["hp"] == 12
    stale = dict(current)
    stale["_rev"] = int(current.get("_rev") or 1) - 1
    stale["hp"] = 8
    stale["lay_on_hands_remaining"] = 0
    stale["spell_slots"] = {"1": 1}
    save_character(cid, stale)
    after = get_character(cid)
    assert after["hp"] == 12
    assert after["lay_on_hands_remaining"] == 5
    assert after["spell_slots"]["1"] == 2


def test_patch_character_merges_without_full_snapshot(isolated_saves):
    from backend.storage import patch_character

    _, cid = _session(isolated_saves, _paladin(hp=8, lay_on_hands_remaining=0))
    patch_character(cid, {"hp": 12, "lay_on_hands_remaining": 5, "spell_slots": {"1": 2}})
    after = get_character(cid)
    assert after["hp"] == 12
    assert after["name"] == "QA Paladin"
    assert after["lay_on_hands_remaining"] == 5


def test_messages_never_shorten_on_stale_write(isolated_saves):
    sid, _cid = _session(isolated_saves)
    persist_user_message(sid, "I take a long rest.")
    persist_shown_reply(sid, "I take a long rest.", "You sleep until dawn.")
    persist_user_message(sid, "I look around.")
    persist_shown_reply(sid, "I look around.", "The mill is quiet.")
    save_session_messages(
        sid,
        [
            {"role": "user", "content": "I take a long rest."},
            {"role": "assistant", "content": "You sleep until dawn."},
        ],
    )
    messages = get_session(sid)["messages"]
    assert len(messages) == 4
    assert messages[-1]["content"] == "The mill is quiet."


def test_lonelog_skips_duplicate_line(isolated_saves):
    sid, _cid = _session(isolated_saves)
    append_session_log(sid, "@ 2026-11-20T10:00:00 Spent 1d10 [4] +2 CON.")
    append_session_log(sid, "@ 2026-11-20T10:00:01 Spent 1d10 [4] +2 CON.")
    content = get_session_lonelog(sid)
    assert content.count("Spent 1d10 [4]") == 1


def test_short_rest_hit_die_uses_one_server_roll(isolated_saves, monkeypatch):
    sid, _cid = _session(isolated_saves)
    monkeypatch.setattr(
        "backend.games.dnd5e.characters.character_builder.random.randint",
        lambda _a, _b: 4,
    )
    with dm_turn_trace(sid, "I take a short rest"):
        updates, logs = apply_mechanics_delta(
            _paladin(hp=5),
            {
                "rest": {"kind": "short", "hit_dice_spent": 1},
                "hp_changes": [{"amount": 6, "source": "Hit Die"}],
            },
        )
    joined = " ".join(logs)
    assert "1d10" in joined
    assert "[4]" in joined
    assert updates["hp"] == 11
    assert joined.count("[6]") == 0
    events = read_audit_events(sid)
    rolls = [row for row in events if row.get("event") == "dice_roll"]
    assert rolls
    assert rolls[0]["detail"]["rolls"] == [4]
    rests = [row for row in events if row.get("event") == "rest"]
    assert rests


def test_bless_concentration_spends_slot(isolated_saves):
    sid, _cid = _session(isolated_saves)
    with dm_turn_trace(sid, "I cast Bless"):
        updates, logs = apply_mechanics_delta(
            _paladin(hp=12, spell_slots={"1": 2}),
            {"concentration": {"action": "start", "spell": "Bless"}},
        )
    assert updates["concentration"] == "Bless"
    assert updates["spell_slots"]["1"] == 1
    assert any("slot" in line.lower() for line in logs)
    events = read_audit_events(sid)
    assert any(row.get("event") == "spell_slot" for row in events)


def test_interrupted_pending_long_rest_applies_short_benefits(isolated_saves):
    sid, _cid = _session(isolated_saves)
    with dm_turn_trace(sid, "I take a long rest"):
        updates, logs = apply_pending_rest(
            _paladin(hp=5, lay_on_hands_remaining=0, spell_slots={"1": 1}),
            {"kind": "long", "dice_to_spend": 1},
            "Goblins kick the door. The rest is interrupted.",
        )
    assert updates.get("lay_on_hands_remaining") in (None, 0)
    assert updates.get("hit_dice_spent") == 1
    assert any("Interrupted rest" in line or "Short rest" in line for line in logs)
    assert not any("did not grant a rest" in line for line in logs)


def test_audit_records_loh_slots_rest_and_condition_dc(isolated_saves):
    sid, _cid = _session(isolated_saves)
    with dm_turn_trace(sid, "I heal then fight"):
        apply_mechanics_delta(
            _paladin(hp=8, lay_on_hands_remaining=5, spell_slots={"1": 2}),
            {
                "resources": {"lay_on_hands": 5},
                "hp_changes": [{"amount": 5, "source": "Lay on Hands"}],
                "conditions": [
                    {"name": "Frightened", "action": "add", "save_dc": 13, "source": "ghost"}
                ],
                "concentration": {"action": "start", "spell": "Bless"},
            },
        )
    events = read_audit_events(sid)
    kinds = {row.get("event") for row in events}
    assert "lay_on_hands" in kinds
    assert "spell_slot" in kinds
    assert "condition" in kinds
    loh = next(row for row in events if row.get("event") == "lay_on_hands")
    assert "5 -> 0" in format_audit_summary(loh)
    cond = next(row for row in events if row.get("event") == "condition")
    assert "DC 13" in format_audit_summary(cond)


def test_sync_player_combatant_does_not_lower_sheet_hp():
    from backend.dm.encounters import CombatState, Combatant
    from backend.games.dnd5e.dm.combat_manager import sync_player_combatant

    state = CombatState(
        encounter_id="e1",
        encounter_name="Ghost",
        status="active",
        combatants=[
            Combatant(id="player", name="Hero", kind="player", hp=8, max_hp=12, ac=18),
        ],
        order=["player"],
    )
    out = sync_player_combatant(state, _paladin(hp=12, max_hp=12))
    assert out["hp"] == 12
    assert state.combatants[0].hp == 12


def test_scribe_skips_narrative_hit_die_when_rest_logged():
    from backend.dm.nodes.bookkeeping import scribe_node

    with patch("backend.dm.nodes.bookkeeping.append_session_log") as append, patch(
        "backend.dm.nodes.bookkeeping.append_adventure_log"
    ), patch("backend.dm.nodes.bookkeeping._rag_direct_tasks", return_value=frozenset()):
        result = scribe_node(
            {
                "session_id": "s1",
                "narrative": "You recover 6 hit points from a Hit Die.",
                "response": "You recover 6 hit points from a Hit Die.",
                "resource_log": ["Interrupted rest (short-rest benefits).", "Spent 1d10 [4] +2 CON -> **6** HP."],
                "character": {"game_id": "dnd5e"},
                "adventure": {},
                "shortcut_result": {"task": "long_rest"},
            }
        )
    joined = " ".join(result.get("lonelog_lines") or [])
    assert "You recover 6" not in joined
    assert append.called
