"""Retest regressions after PR #16: migration, MI free cast, rest/AC/HP sync, lookup, scribe."""

from backend.dm.nodes.bookkeeping import _cheap_lonelog_summary
from backend.games.dnd5e.characters.character_builder import (
    long_rest_recover,
    rebuild_character,
)
from backend.games.dnd5e.characters.class_resources import compute_ac_details
from backend.games.dnd5e.characters.creation_choices import (
    migrate_legacy_sheet,
    validate_creation_choices,
)
from backend.games.dnd5e.characters.entity import character_from_dict
from backend.games.dnd5e.characters.spell_resources import (
    apply_spell_cast,
    is_spell_available,
    match_spell_name,
    normalize_spell_name,
)
from backend.games.dnd5e.dm.agents.nodes import resource_keeper_node
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_rest,
    narrative_short_rest_detected,
    parse_pc_hp_from_narration,
    rest_granted,
    rest_refused,
)
from backend.games.dnd5e.dm.spell_autocomplete import list_character_spells, resolve_spell_query
from backend.games.registry import _migration_fields


def _legacy_wizard() -> dict:
    return {
        "name": "QA Wizard",
        "species": "elf",
        "class_name": "wizard",
        "level": 1,
        "background": "sage",
        "origin_feat": "Magic Initiate (Wizard)",
        "ability_scores": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        "ability_scores_set": True,
        "hp": 8,
        "max_hp": 8,
        "ac": 12,
        "armor": "none",
        "cantrips": ["Fire Bolt", "Mage Hand", "Prestidigitation"],
        "prepared_spells": ["Detect Magic", "Mage Armor", "Magic Missile", "Shield"],
        "spellbook": [],
        "languages": ["common"],
        "spell_slots": {"1": 2},
        "feature_choices": {"elven_lineage": "high_elf"},
        "classes": [{"class_name": "wizard", "level": 1}],
    }


def test_migrate_seeds_spellbook_and_high_elf_ability():
    char = character_from_dict(_legacy_wizard())
    assert migrate_legacy_sheet(char) is True
    rebuilt = rebuild_character(char)
    assert "mage armor" in [s.lower() for s in rebuilt.spellbook]
    assert len({s.lower() for s in rebuilt.spellbook}) >= 6
    assert rebuilt.feature_choices.get("high_elf_spell_ability") == "int"
    assert rebuilt.hp == 8
    assert rebuilt.spell_slots["1"] == 2


def test_migrate_infers_origin_languages_without_wiping():
    data = {
        "name": "QA Paladin",
        "species": "dwarf",
        "class_name": "paladin",
        "level": 1,
        "languages": ["common", "dwarvish", "elvish"],
        "feature_choices": {},
        "ability_scores": {"str": 15, "dex": 10, "con": 14, "int": 8, "wis": 12, "cha": 13},
        "ability_scores_set": True,
        "hp": 12,
        "max_hp": 12,
    }
    char = rebuild_character(character_from_dict(data))
    origin = [str(x).lower() for x in char.feature_choices.get("origin_languages") or []]
    assert "dwarvish" in origin
    assert "elvish" in origin
    assert "dwarvish" in char.languages
    missing = validate_creation_choices(char)
    assert not any("origin languages" in m.lower() for m in missing)


def test_rebuild_dict_does_not_wipe_hp_or_slots():
    from backend.games.dnd5e.characters.entity import character_to_dict

    data = _legacy_wizard()
    data["hp"] = 3
    data["spell_slots"] = {"1": 0}
    rebuilt = character_to_dict(rebuild_character(character_from_dict(data)))
    assert rebuilt["hp"] == 3
    assert rebuilt["spell_slots"]["1"] == 0
    assert rebuilt["spellbook"]
    assert _migration_fields(data) != _migration_fields(rebuilt)


def test_mage_armor_lookup_and_ac():
    char = rebuild_character(character_from_dict(_legacy_wizard()))
    assert is_spell_available(char, "Mage Armor")
    assert is_spell_available(char, "Mage Armor, last slot")
    assert match_spell_name(char, "Mage Armor, last slot")
    assert normalize_spell_name("Mage Armour") == "magearmor"
    names = [n.lower() for n in list_character_spells(char)]
    assert "mage armor" in names
    ok, msg = apply_spell_cast(char, "Mage Armor, last slot", requested_text="Cast Mage Armor, last slot")
    assert ok
    assert "slot" in msg.lower()
    assert char.spell_slots["1"] == 1
    details = compute_ac_details(char)
    assert details["computed"] == 15
    assert char.ac == 15 or details["ac"] == 15


def test_magic_initiate_free_cast_does_not_spend_slot():
    data = _legacy_wizard()
    data["feature_choices"] = {
        "elven_lineage": "high_elf",
        "magic_initiate_level1": "Shield",
        "magic_initiate_cantrips": ["Minor Illusion", "Acid Splash"],
    }
    char = rebuild_character(character_from_dict(data))
    ok, msg = apply_spell_cast(
        char,
        "Shield",
        requested_text="Yes, cast Shield (Magic Initiate free)",
        free_use=True,
    )
    assert ok
    assert "no slot" in msg.lower()
    assert char.spell_slots["1"] == 2
    assert char.feature_choices.get("_magic_initiate_free_used") is True
    ok2, _ = apply_spell_cast(char, "Shield", free_use=True, requested_text="Magic Initiate free")
    assert ok2
    assert char.spell_slots["1"] == 1
    long_rest_recover(char)
    assert not char.feature_choices.get("_magic_initiate_free_used")


def test_unset_mi_spell_honors_explicit_free_request():
    char = rebuild_character(character_from_dict(_legacy_wizard()))
    ok, msg = apply_spell_cast(
        char,
        "Shield",
        requested_text="Yes, cast Shield (Magic Initiate free)",
        free_use=True,
    )
    assert ok
    assert "magic initiate" in msg.lower()
    assert char.spell_slots["1"] == 2


def test_rest_refused_does_not_apply_pending_rest():
    data = _legacy_wizard()
    data["hp"] = 5
    data["spell_slots"] = {"1": 0}
    refused = (
        "Short rest: not possible. Mott is less than a minute away. Automated result not applied."
    )
    assert rest_refused(refused)
    assert not rest_granted(refused, kind="short")
    assert not narrative_short_rest_detected("**Short rest**", refused)
    entity, logs = apply_pending_rest(
        data, {"kind": "short", "dice_to_spend": 1}, refused
    )
    assert entity == {}
    assert any("not applied" in line.lower() for line in logs)


def test_rest_granted_applies_pending_rest():
    data = _legacy_wizard()
    data["hp"] = 5
    data["spell_slots"] = {"1": 0}
    from backend.games.dnd5e.dm.mechanics_delta import render_mechanics_block

    granted = (
        "You settle in for an hour. Arcane Recovery restores a slot as you rest.\n"
        + render_mechanics_block({"rest": {"kind": "short", "hit_dice_spent": 1}})
    )
    assert rest_granted(granted, kind="short")
    entity, logs = apply_pending_rest(
        data, {"kind": "short", "dice_to_spend": 1}, granted
    )
    assert entity.get("spell_slots", {}).get("1") == 1
    assert any("rest" in line.lower() for line in logs)


def test_resource_keeper_applies_short_rest_only_when_granted():
    state = {
        "shortcut_result": {
            "task": "short_rest",
            "pending_rest": {"kind": "short", "dice_to_spend": 1},
        },
        "response": "Short rest: not possible. An enemy is approaching.",
        "character": _legacy_wizard(),
        "user_message": "**Short rest**",
    }
    result = resource_keeper_node(state)
    updates = result.get("character_updates") or {}
    assert "hit_dice_spent" not in updates
    assert any("not applied" in line.lower() for line in result.get("resource_log") or [])


def test_hp_from_narration_is_authoritative():
    hp = parse_pc_hp_from_narration(
        "The arrow drops you to 3/8 HP. Leave things at 3 HP, no retcon.",
        name="QA Wizard",
        max_hp=8,
        current_hp=8,
    )
    assert hp == 3
    from backend.games.dnd5e.dm.agents.nodes import _needs_resource_keeper

    assert _needs_resource_keeper(
        {
            "user_message": "Leave things at 3 HP, no retcon.",
            "response": "HP 3/8. No retcon.",
            "shortcut_result": {},
        }
    )


def test_extract_cast_yes_cast_shield_free():
    from backend.games.dnd5e.dm.spell_autocomplete import extract_cast_query

    query = extract_cast_query("Yes, cast Shield (Magic Initiate free)")
    assert query
    char = rebuild_character(character_from_dict(_legacy_wizard()))
    res = resolve_spell_query(char, query)
    assert res.status == "exact"
    assert "shield" in res.spell_name.lower()


def test_spell_query_mage_armor_last_slot_is_exact():
    char = rebuild_character(character_from_dict(_legacy_wizard()))
    res = resolve_spell_query(char, "Mage Armor, last slot")
    assert res.status == "exact"
    assert "mage armor" in res.spell_name.lower()


def test_short_rest_shortcut_does_not_apply_until_dm_grants():
    from backend.games.dnd5e.actions import run_shortcut

    result = run_shortcut("short_rest", **_legacy_wizard())
    assert result["task"] == "short_rest"
    assert result.get("entity_updates") == {}
    assert result.get("pending_rest", {}).get("kind") == "short"


def test_cast_spell_shortcut_without_name_does_not_spend():
    from backend.games.dnd5e.actions import run_shortcut

    result = run_shortcut("cast_spell", **_legacy_wizard())
    assert result["task"] == "cast_spell"
    assert result.get("entity_updates") == {}
    assert "no spell named" in result["user_message"].lower()


def test_cast_spell_shortcut_mage_armor_sets_ac_and_spends_slot():
    from backend.games.dnd5e.actions import run_shortcut
    from backend.games.dnd5e.dm.resource_keeper import apply_pending_cast

    data = _legacy_wizard()
    result = run_shortcut("cast_spell", spell_name="Mage Armor", **data)
    assert result.get("entity_updates") == {}
    pending = result.get("pending_cast") or {}
    assert pending.get("spell_name") == "Mage Armor"
    updates, _logs = apply_pending_cast(data, pending, "The ward settles over you. AC 15.")
    assert updates.get("spell_slots", {}).get("1") == 1
    assert updates.get("ac") == 15
    assert "Mage Armor" in result["user_message"] or "mage armor" in result["user_message"].lower()


def test_cast_spell_shortcut_mi_free_keeps_slot():
    from backend.games.dnd5e.actions import run_shortcut
    from backend.games.dnd5e.dm.resource_keeper import apply_pending_cast

    data = _legacy_wizard()
    data["feature_choices"] = {
        **(data.get("feature_choices") or {}),
        "magic_initiate_level1": "Shield",
        "magic_initiate_cantrips": ["Light", "Prestidigitation"],
        "magic_initiate_ability": "int",
    }
    result = run_shortcut(
        "cast_spell",
        spell_name="Shield",
        free_use=True,
        requested_text="Shield Magic Initiate free",
        **data,
    )
    assert result.get("entity_updates") == {}
    pending = result.get("pending_cast") or {}
    updates, logs = apply_pending_cast(data, pending, "A shimmering shield snaps into place.")
    assert updates.get("spell_slots", {}).get("1") == 2
    assert any("no slot" in line.lower() for line in logs)


def test_scribe_uses_cheap_summary_not_llm():
    import inspect

    from backend.dm.nodes import bookkeeping

    source = inspect.getsource(bookkeeping.scribe_node)
    assert "synthesize_lonelog_summary" not in source
    assert "_cheap_lonelog_summary" in source
    summary = _cheap_lonelog_summary("First sentence. Second sentence. Third is ignored.")
    assert "First sentence" in summary
    assert "Third" not in summary
