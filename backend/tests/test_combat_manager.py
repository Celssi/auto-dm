"""Combat manager initiative and enemy turn tests."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import backend.config as cfg
from backend.dm.combat_manager import (
    advance_turn,
    apply_damage_to_player,
    current_combatant,
    pick_encounter_to_start,
    resolve_enemy_attack,
    start_encounter,
)
from backend.dm.encounters import (
    CombatState,
    Combatant,
    EncounterEnemySpec,
    EncounterSpec,
    save_adventure_encounters,
)
from backend.dm.monster_resolver import MonsterAttack, MonsterStats


def _char_dict(hp: int = 30, ac: int = 15) -> dict:
    return {
        "name": "Test Hero",
        "hp": hp,
        "max_hp": hp,
        "ac": ac,
        "ability_scores": {"dex": 14},
    }


def test_advance_turn_wraps_round():
    state = CombatState(
        encounter_id="e1",
        encounter_name="Test",
        order=["a", "b"],
        turn_index=1,
        round=1,
        combatants=[
            Combatant(id="a", name="A", kind="player", initiative=18, hp=10, max_hp=10, ac=14),
            Combatant(id="b", name="B", kind="enemy", initiative=10, hp=10, max_hp=10, ac=12),
        ],
    )
    state = advance_turn(state)
    assert state.turn_index == 0
    assert state.round == 2


def test_resolve_enemy_attack_nat_20_hits():
    with patch("backend.dm.combat_manager.roll_dice") as roll:
        roll.side_effect = [
            {"rolls": [20], "total": 20},
            {"total": 7},
        ]
        enemy = Combatant(
            id="e1",
            name="Goblin",
            kind="enemy",
            initiative=12,
            hp=7,
            max_hp=7,
            ac=15,
            attack_bonus=4,
            damage="1d6+2",
        )
        result = resolve_enemy_attack(enemy, target_ac=18)
    assert result["hit"] is True
    assert result["crit"] is True
    assert result["damage"] == 7


def test_apply_damage_to_player():
    updated = apply_damage_to_player(_char_dict(hp=20), 5)
    assert updated["hp"] == 15


def test_start_encounter_and_initiative_order():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    session_id = "sess-1"
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

    with patch("backend.dm.combat_manager.lookup_monster", return_value=fake_stats):
        with patch("backend.dm.combat_manager._roll_initiative", side_effect=[15, 10, 8]):
            state = start_encounter(session_id, encounter, _char_dict())

    assert state.encounter_name == "Merrow Raid"
    assert len(state.combatants) == 2
    assert state.order[0] == "player"
    assert current_combatant(state).kind == "player"


def test_pick_encounter_auto_on_beat_match():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    adv_id = "adv-test"
    save_adventure_encounters(
        adv_id,
        [
            EncounterSpec(
                id="e1",
                name="Ambush",
                trigger_beat="Dock fight",
                description="Merrow attack the harbor.",
                enemies=[EncounterEnemySpec(monster_name="Merrow", count=2)],
            )
        ],
    )
    picked = pick_encounter_to_start(
        adv_id,
        session_id="sess-1",
        active_beat="Blood on the Docks",
        active_beat_notes="ENCOUNTER: 3-5 merrow surge from the black water onto the harbor docks.",
        user_message="I look around nervously",
    )
    assert picked is not None
    assert picked.name == "Ambush"


def test_pick_encounter_not_early_on_setup_beat():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    adv_id = "adv-test"
    save_adventure_encounters(
        adv_id,
        [
            EncounterSpec(
                id="e1",
                name="Merrow Harbor Raid",
                trigger_beat="Merrow raid",
                description="Merrow attack the harbor.",
                enemies=[EncounterEnemySpec(monster_name="Merrow", count=2)],
            )
        ],
    )
    assert (
        pick_encounter_to_start(
            adv_id,
            session_id="sess-1",
            active_beat="The Tide Moot",
            active_beat_notes="Prove your worth by dealing with the merrow raiding party later.",
            user_message="I ask Marceska about passage",
        )
        is None
    )


def test_completed_encounter_not_restarted():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    adv_id = "adv-test"
    session_id = "sess-done"
    save_adventure_encounters(
        adv_id,
        [
            EncounterSpec(
                id="e1",
                name="Ambush",
                trigger_beat="Dock fight",
                enemies=[EncounterEnemySpec(monster_name="Merrow", count=2)],
            )
        ],
    )
    enc.mark_encounter_completed(session_id, "e1")
    assert (
        pick_encounter_to_start(
            adv_id,
            session_id=session_id,
            active_beat="Dock fight",
            user_message="I attack",
        )
        is None
    )
