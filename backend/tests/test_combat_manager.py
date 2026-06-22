"""Combat manager initiative and enemy turn tests."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import backend.config as cfg
from backend.dm.encounters import (
    Combatant,
    CombatState,
    EncounterEnemySpec,
    EncounterSpec,
    save_adventure_encounters,
)
from backend.games.dnd5e.characters.entity import character_from_dict
from backend.games.dnd5e.dm.combat_manager import (
    advance_turn,
    apply_damage_to_player,
    check_concentration_save,
    current_combatant,
    pick_encounter_to_start,
    resolve_enemy_attack,
    resolve_enemy_turn,
    start_encounter,
)
from backend.games.dnd5e.dm.monster_resolver import MonsterAttack, MonsterStats


def _char_dict(hp: int = 30, ac: int = 15, **extras) -> dict:
    base = {
        "name": "Test Hero",
        "hp": hp,
        "max_hp": hp,
        "ac": ac,
        "ability_scores": {"dex": 14, "con": 12},
    }
    base.update(extras)
    return base


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
    with patch("backend.games.dnd5e.dm.combat_manager.roll_dice") as roll:
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

    patch_path = "backend.games.dnd5e.dm.combat_manager._roll_initiative"
    with patch("backend.games.dnd5e.dm.combat_manager.lookup_monster", return_value=fake_stats):
        with patch(patch_path, side_effect=[15, 10, 8]):
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


def test_pick_encounter_not_on_shared_harbor_word():
    """Merrow Harbor Raid must not match The Dying Harbor via 'harbor' alone."""
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    adv_id = "adv-harbor"
    save_adventure_encounters(
        adv_id,
        [
            EncounterSpec(
                id="merrow-raid",
                name="Merrow Harbor Raid",
                trigger_beat="Merrow raid",
                description="Merrow attack Salthollow docks.",
                enemies=[EncounterEnemySpec(monster_name="Merrow", count=3)],
            )
        ],
    )
    assert (
        pick_encounter_to_start(
            adv_id,
            session_id="sess-1",
            active_beat="The Dying Harbor",
            active_beat_notes="Explore Salthollow; fish are dying; tension at the gate.",
            user_message="I'll ask her what's really going on down in that harbor",
            recent_dm_text="Dalla blocks the gate. The alarm bell rings below.",
        )
        is None
    )


def test_try_start_skips_social_turn_without_combat_scene():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    adv_id = "adv-harbor"
    session_id = "sess-social"
    save_adventure_encounters(
        adv_id,
        [
            EncounterSpec(
                id="merrow-raid",
                name="Merrow Harbor Raid",
                trigger_beat="Blood on the Docks",
                description="Merrow attack the harbor.",
                enemies=[EncounterEnemySpec(monster_name="Merrow", count=2)],
            )
        ],
    )
    from backend.games.dnd5e.dm.combat_manager import try_start_planned_encounter

    state = try_start_planned_encounter(
        session_id,
        adv_id,
        _char_dict(),
        user_message="I ask Dalla about the harbor",
        messages=[{"role": "assistant", "content": "Dalla waits at the gate."}],
    )
    assert state is None


def test_new_combat_does_not_auto_run_enemy_turns():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.dm.encounters as enc

    enc.SAVES_DIR = tmpdir
    session_id = "sess-new"
    encounter = EncounterSpec(
        id="e1",
        name="Ambush",
        enemies=[EncounterEnemySpec(monster_name="Merrow", count=1)],
    )
    fake_stats = MonsterStats(
        name="Merrow",
        ac=13,
        hp=45,
        attacks=[MonsterAttack(name="Harpoon", to_hit=6, damage="2d6+3")],
    )
    with patch("backend.games.dnd5e.dm.combat_manager.lookup_monster", return_value=fake_stats):
        with patch(
            "backend.games.dnd5e.dm.combat_manager._roll_initiative",
            side_effect=[10, 18],
        ):
            start_encounter(session_id, encounter, _char_dict(hp=12))
    from backend.games.dnd5e.dm.combat_manager import (
        current_combatant,
        run_enemy_turns_until_player,
    )

    _, char, events = run_enemy_turns_until_player(
        session_id, _char_dict(hp=12), resolve_enemies=False
    )
    assert current_combatant(enc.load_combat_state(session_id)).kind == "enemy"
    assert char["hp"] == 12
    assert events == []


def test_player_took_combat_action():
    from backend.games.dnd5e.dm.combat_manager import player_took_combat_action

    assert player_took_combat_action("I ask about the harbor") is False
    assert player_took_combat_action("I attack the merrow") is True
    assert player_took_combat_action("", {"task": "attack_roll"}) is True


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


def test_concentration_save_success_on_low_damage():
    char = character_from_dict(_char_dict(concentration="Bless", class_name="fighter"))
    with patch("backend.games.dnd5e.dm.combat_manager.roll_dice") as roll:
        roll.return_value = {"rolls": [15], "total": 15}
        maintained, summary = check_concentration_save(char, 8)
    assert maintained is True
    assert "MAINTAINED" in summary
    assert "Bless" in summary


def test_concentration_save_failure():
    char = character_from_dict(_char_dict(concentration="Bless", class_name="wizard"))
    with patch("backend.games.dnd5e.dm.combat_manager.roll_dice") as roll:
        roll.return_value = {"rolls": [3], "total": 3}
        maintained, summary = check_concentration_save(char, 30)
    assert maintained is False
    assert "LOST" in summary
    assert "DC 15" in summary


def test_concentration_save_not_triggered_without_spell():
    char = character_from_dict(_char_dict())
    maintained, summary = check_concentration_save(char, 20)
    assert maintained is True
    assert summary == ""


def test_concentration_dc_minimum_is_10():
    char = character_from_dict(_char_dict(concentration="Shield of Faith"))
    with patch("backend.games.dnd5e.dm.combat_manager.roll_dice") as roll:
        roll.return_value = {"rolls": [9], "total": 9}
        maintained, summary = check_concentration_save(char, 4)
    assert "DC 10" in summary


def test_multiattack_enemy_makes_multiple_attacks():
    state = CombatState(
        encounter_id="e1",
        encounter_name="Dragon Fight",
        order=["enemy1", "player"],
        turn_index=0,
        round=1,
        combatants=[
            Combatant(
                id="enemy1",
                name="Dragon",
                kind="enemy",
                initiative=20,
                hp=100,
                max_hp=100,
                ac=18,
                attack_bonus=8,
                damage="2d6+4",
                multiattack_count=3,
            ),
            Combatant(
                id="player",
                name="Hero",
                kind="player",
                initiative=10,
                hp=40,
                max_hp=40,
                ac=15,
            ),
        ],
    )
    attack_rolls = [
        {"rolls": [15], "total": 15},
        {"total": 10},
        {"rolls": [18], "total": 18},
        {"total": 12},
        {"rolls": [5], "total": 5},
    ]
    with patch("backend.games.dnd5e.dm.combat_manager.roll_dice", side_effect=attack_rolls):
        state, char_dict, events = resolve_enemy_turn(state, _char_dict(hp=40))
    multiattack_events = [e for e in events if "Multiattack" in e]
    attack_events = [e for e in events if "attacks" in e.lower() and "Multiattack" not in e]
    assert len(multiattack_events) == 1
    assert len(attack_events) == 3


def test_enemy_attack_breaks_concentration():
    state = CombatState(
        encounter_id="e1",
        encounter_name="Test",
        order=["enemy1", "player"],
        turn_index=0,
        round=1,
        combatants=[
            Combatant(
                id="enemy1",
                name="Orc",
                kind="enemy",
                initiative=15,
                hp=15,
                max_hp=15,
                ac=13,
                attack_bonus=5,
                damage="1d12+3",
            ),
            Combatant(
                id="player",
                name="Hero",
                kind="player",
                initiative=10,
                hp=30,
                max_hp=30,
                ac=15,
            ),
        ],
    )
    char = _char_dict(hp=30, concentration="Bless", class_name="wizard")
    roll_sequence = [
        {"rolls": [18], "total": 18},
        {"total": 10},
        {"rolls": [2], "total": 2},
    ]
    with patch("backend.games.dnd5e.dm.combat_manager.roll_dice", side_effect=roll_sequence):
        state, updated_char, events = resolve_enemy_turn(state, char)
    conc_events = [e for e in events if "Concentration" in e]
    assert len(conc_events) == 1
    assert "LOST" in conc_events[0]
    assert updated_char["concentration"] == ""
