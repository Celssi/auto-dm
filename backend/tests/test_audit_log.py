"""Session audit log tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import backend.config as cfg
from backend import journal_storage, storage
from backend.characters.entity import character_from_dict
from backend.characters.spell_resources import apply_resource_updates
from backend.dm.actions import run_shortcut
from backend.dm.audit import read_audit_events, record_audit
from backend.dm.combat_manager import apply_damage_to_player, start_encounter
from backend.dm.encounters import EncounterEnemySpec, EncounterSpec
from backend.dm.graph import character_keeper_node
from backend.dm.monster_resolver import MonsterAttack, MonsterStats
from backend.dm.resource_keeper import ResourceTurnUpdates, SpellCast
from backend.dm.trace import audit_session_context
from backend.play_tools import roll_dice


def _druid_char(**overrides) -> dict:
    base = {
        "name": "Test Druid",
        "class_name": "druid",
        "subclass": "Circle of the Moon",
        "level": 3,
        "cantrips": ["druidcraft", "produce flame"],
        "prepared_spells": ["healing word", "moonbeam", "cure wounds"],
        "spell_slots": {"1": 4, "2": 2},
        "wild_shape_uses": 2,
        "classes": [{"class_name": "druid", "level": 3, "subclass": "Circle of the Moon"}],
    }
    base.update(overrides)
    return base


@pytest.fixture
def saves_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sessions_dir = tmp_path / "sessions"
    characters_dir = tmp_path / "characters"
    adventures_dir = tmp_path / "adventures"
    monkeypatch.setattr(storage, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(storage, "CHARACTERS_DIR", characters_dir)
    monkeypatch.setattr(storage, "ADVENTURES_DIR", adventures_dir)
    monkeypatch.setattr(storage, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(journal_storage, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(cfg, "SAVES_DIR", tmp_path)
    characters_dir.mkdir(parents=True, exist_ok=True)
    adventures_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    journal_storage.CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    yield tmp_path


def test_storage_append_read_round_trip(saves_dir: Path):
    storage.append_session_audit("sess-1", {"event": "test", "source": "unit"})
    events = storage.get_session_audit("sess-1")
    assert len(events) == 1
    assert events[0]["event"] == "test"
    assert events[0]["source"] == "unit"
    assert "ts" in events[0]


def test_record_audit_via_module(saves_dir: Path):
    record_audit(
        {"event": "dice_roll", "source": "test", "detail": {"notation": "1d6", "total": 4}},
        session_id="sess-2",
    )
    events = read_audit_events("sess-2")
    assert len(events) == 1
    assert events[0]["session_id"] == "sess-2"


def test_roll_dice_produces_audit_with_session_context(saves_dir: Path):
    with audit_session_context("sess-dice"):
        roll_dice("1d20+3", caller="shortcut.test")
    events = read_audit_events("sess-dice")
    dice = [e for e in events if e["event"] == "dice_roll"]
    assert len(dice) == 1
    assert dice[0]["detail"]["notation"] == "1d20+3"
    assert dice[0]["detail"]["inferred"] is False


def test_death_save_audit_counter_delta(saves_dir: Path):
    with audit_session_context("sess-ds"):
        run_shortcut(
            "death_save",
            hp=0,
            max_hp=30,
            death_save_successes=1,
            death_save_failures=0,
            pre_rolled=[12],
        )
    events = read_audit_events("sess-ds")
    ds = [e for e in events if e["event"] == "death_save"]
    assert len(ds) == 1
    assert ds[0]["before"]["death_save_successes"] == 1
    assert ds[0]["after"]["death_save_successes"] == 2
    assert ds[0]["detail"]["roll"] == 12
    assert ds[0]["detail"]["inferred"] is False


def test_apply_damage_produces_hp_change(saves_dir: Path):
    with audit_session_context("sess-hp"):
        apply_damage_to_player({"hp": 20, "max_hp": 20, "name": "Hero"}, 5)
    events = read_audit_events("sess-hp")
    hc = [e for e in events if e["event"] == "hp_change"]
    assert len(hc) == 1
    assert hc[0]["before"]["hp"] == 20
    assert hc[0]["after"]["hp"] == 15
    assert hc[0]["detail"]["damage"] == 5


def test_character_keeper_node_produces_patch_diff(saves_dir: Path):
    state = {
        "session_id": "sess-patch",
        "character": {"hp": 10, "max_hp": 20, "spell_slots": {"1": 2}},
        "character_updates": {"hp": 8},
    }
    character_keeper_node(state)
    events = read_audit_events("sess-patch")
    cp = [e for e in events if e["event"] == "character_patch"]
    assert len(cp) == 1
    assert "hp" in cp[0]["diff"]
    assert cp[0]["before"]["hp"] == 10
    assert cp[0]["after"]["hp"] == 8


def test_combat_start_logs_initiative(saves_dir: Path):
    import backend.dm.encounters as enc

    enc.SAVES_DIR = saves_dir
    encounter = EncounterSpec(
        id="merrow-raid",
        name="Merrow Raid",
        enemies=[EncounterEnemySpec(monster_name="Merrow", count=1)],
    )
    fake_stats = MonsterStats(
        name="Merrow",
        ac=13,
        hp=45,
        attacks=[MonsterAttack(name="Harpoon", to_hit=6, damage="2d6+3")],
    )
    char = {"name": "Hero", "hp": 30, "max_hp": 30, "ac": 15, "ability_scores": {"dex": 14}}

    with patch("backend.dm.combat_manager.lookup_monster", return_value=fake_stats):
        with patch("backend.dm.combat_manager._roll_initiative", side_effect=[15, 10]):
            start_encounter("sess-combat", encounter, char)

    events = read_audit_events("sess-combat")
    cs = [e for e in events if e["event"] == "combat_start"]
    assert len(cs) == 1
    initiative = cs[0]["detail"]["initiative"]
    assert isinstance(initiative, list)
    assert len(initiative) == 2
    values = {entry["id"]: entry["initiative"] for entry in initiative}
    assert values["player"] == 15


def test_inferred_resource_keeper_cast_tagged(saves_dir: Path):
    char = character_from_dict(_druid_char())
    updates = ResourceTurnUpdates(casts=[SpellCast(spell_name="Healing Word")])
    with audit_session_context("sess-inf"):
        apply_resource_updates(char, updates, audit_source="resource_keeper", inferred=True)
    events = read_audit_events("sess-inf")
    tagged = [e for e in events if e.get("detail", {}).get("inferred") is True]
    assert tagged
    assert any(e["event"] == "spell_cast" for e in tagged)
    assert any(e["event"] == "spell_slot" for e in tagged)
