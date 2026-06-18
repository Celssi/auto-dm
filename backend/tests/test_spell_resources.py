"""Spell slot, wild shape, and resource keeper tests."""

from __future__ import annotations

from backend.characters.character_builder import apply_short_rest, long_rest_recover, rebuild_character
from backend.characters.entity import character_from_dict, character_to_dict
from backend.characters.spell_resources import (
    apply_resource_updates,
    apply_spell_cast,
    compute_pact_spell_slots,
    compute_wild_shape_max,
    recover_pact_slots_on_short_rest,
)
from backend.dm.graph import resource_keeper_node
from backend.dm.resource_keeper import (
    ResourceTurnUpdates,
    apply_cast_spell_shortcut,
    narrative_short_rest_detected,
    run_resource_keeper,
)


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


def test_cantrip_does_not_spend_slot():
    char = character_from_dict(_druid_char())
    ok, msg = apply_spell_cast(char, "Druidcraft")
    assert ok
    assert "no slot" in msg.lower()
    assert char.spell_slots["1"] == 4


def test_first_level_spell_spends_l1_slot():
    char = character_from_dict(_druid_char())
    ok, _ = apply_spell_cast(char, "Healing Word")
    assert ok
    assert char.spell_slots["1"] == 3


def test_upcast_spends_higher_slot():
    char = character_from_dict(_druid_char(spell_slots={"1": 4, "2": 2}))
    ok, msg = apply_spell_cast(char, "Healing Word", slot_level=2)
    assert ok
    assert char.spell_slots["2"] == 1
    assert char.spell_slots["1"] == 4
    assert "upcast" in msg.lower() or "level 2" in msg.lower()


def test_ritual_does_not_spend_slot():
    char = character_from_dict(_druid_char())
    ok, msg = apply_spell_cast(char, "Healing Word", ritual=True)
    assert ok
    assert "ritual" in msg.lower()
    assert char.spell_slots["1"] == 4


def test_rebuild_character_preserves_spent_slots():
    data = _druid_char(spell_slots={"1": 2, "2": 2})
    char = rebuild_character(character_from_dict(data))
    assert char.spell_slots["1"] == 2
    assert char.spell_slots["2"] == 2


def test_long_rest_restores_slots_and_wild_shape():
    char = character_from_dict(_druid_char(spell_slots={"1": 1, "2": 0}, wild_shape_uses=0))
    rest = long_rest_recover(char)
    assert char.spell_slots["1"] == 4
    assert char.spell_slots["2"] == 2
    assert char.wild_shape_uses == 2
    assert char.concentration == ""
    assert "Wild Shape" in rest["summary"]


def test_elf_long_rest_includes_trance_note():
    char = character_from_dict(_druid_char(species="elf"))
    rest = long_rest_recover(char)
    assert "Trance" in rest["summary"]
    assert "4" in rest["summary"]


def test_wild_shape_use_decrements():
    char = character_from_dict(_druid_char())
    updates = ResourceTurnUpdates(wild_shape_used=True)
    _, logs = apply_resource_updates(char, updates)
    assert char.wild_shape_uses == 1
    assert any("Wild Shape" in line for line in logs)


def test_compute_wild_shape_max_druid():
    char = character_from_dict(_druid_char())
    assert compute_wild_shape_max(char) == 2
    fighter = character_from_dict({"class_name": "fighter", "level": 5})
    assert compute_wild_shape_max(fighter) == 0


def test_cast_spell_shortcut():
    data = _druid_char()
    entity, logs = apply_cast_spell_shortcut(data, "Healing Word")
    assert entity["spell_slots"]["1"] == 3
    assert logs and "Healing Word" in logs[0]


def test_resource_keeper_node_skips_rules_help():
    state = {
        "shortcut_result": {"task": "rules_help"},
        "response": "Some narrative",
        "character": _druid_char(),
        "user_message": "cast fireball",
    }
    assert resource_keeper_node(state) == {}


def test_resource_keeper_node_skips_empty_narrative():
    state = {
        "shortcut_result": {},
        "response": "",
        "character": _druid_char(),
        "user_message": "hello",
    }
    assert resource_keeper_node(state) == {}


def test_subclass_always_prepared_spell_available():
    char = character_from_dict(
        _druid_char(prepared_spells=["healing word"], subclass="Circle of the Moon")
    )
    ok, _ = apply_spell_cast(char, "Moonbeam")
    assert ok
    assert char.spell_slots["2"] == 1


def _warlock_char(**overrides) -> dict:
    base = {
        "name": "Test Warlock",
        "class_name": "warlock",
        "level": 3,
        "cantrips": ["eldritch blast"],
        "known_spells": ["hex", "armor of agathys"],
        "spell_slots": {"2": 0},
        "classes": [{"class_name": "warlock", "level": 3}],
    }
    base.update(overrides)
    return base


def test_warlock_pact_slots_recover_on_short_rest():
    char = character_from_dict(_warlock_char(spell_slots={"2": 0}))
    assert compute_pact_spell_slots(char) == {"2": 2}
    line = recover_pact_slots_on_short_rest(char)
    assert line and "Pact Magic" in line
    assert char.spell_slots["2"] == 2


def test_apply_short_rest_warlock_without_hit_dice():
    char = character_from_dict(_warlock_char(spell_slots={"2": 1}))
    rest = apply_short_rest(char, dice_to_spend=0)
    assert char.spell_slots["2"] == 2
    assert "Pact Magic" in rest["summary"]


def test_druid_short_rest_does_not_restore_spell_slots():
    char = character_from_dict(_druid_char(spell_slots={"1": 2, "2": 1}))
    apply_short_rest(char, dice_to_spend=0)
    assert char.spell_slots == {"1": 2, "2": 1}


def test_narrative_short_rest_detected():
    assert narrative_short_rest_detected("We take a short rest.", "You settle in for an hour.")
    assert not narrative_short_rest_detected("We take a long rest.", "Eight hours pass.")


def test_narrative_short_rest_via_resource_keeper(monkeypatch):
    data = _warlock_char(spell_slots={"2": 0})
    entity, logs = run_resource_keeper(
        character=data,
        user_message="I take a short rest by the fire.",
        dm_response="An hour passes. You feel your patron's power return.",
    )
    assert entity["spell_slots"]["2"] == 2
    assert logs and "Short rest" in logs[0]


def test_resource_keeper_node_skips_short_rest_shortcut():
    state = {
        "shortcut_result": {"task": "short_rest"},
        "response": "You rest.",
        "character": _warlock_char(),
        "user_message": "short rest",
    }
    assert resource_keeper_node(state) == {}

