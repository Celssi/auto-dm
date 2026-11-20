"""Reproduce live QA of PR #17 against the three production character shapes."""

from backend.dm.lonelog import is_empty_spell_warning, sanitize_lonelog_content
from backend.games.dnd5e.characters.character_builder import rebuild_character
from backend.games.dnd5e.characters.class_resources import compute_ac_details
from backend.games.dnd5e.characters.creation_choices import (
    migrate_legacy_sheet,
    validate_creation_choices,
)
from backend.games.dnd5e.characters.entity import character_from_dict, character_to_dict
from backend.games.dnd5e.characters.spell_resources import (
    apply_resource_updates,
    apply_spell_cast,
    magic_initiate_free_available,
    magic_initiate_spell_name,
)
from backend.games.dnd5e.dm.agents.nodes import _needs_continuity_guard
from backend.games.dnd5e.dm.resource_keeper import overlay_live_resources, parse_pc_hp_from_narration
from backend.games.registry import _migration_fields, preserve_live_resources


def _live_wizard() -> dict:
    """QA Wizard b819a0ec as loaded after PR #17 (Common only, 4 prepared, missing 2024 picks)."""
    return {
        "id": "b819a0ec",
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
        "hit_dice_max": 1,
        "hit_dice_spent": 1,
        "cantrips": ["Fire Bolt", "Mage Hand", "Prestidigitation"],
        "prepared_spells": ["Detect Magic", "Mage Armor", "Magic Missile", "Shield"],
        "spellbook": ["Detect Magic", "Mage Armor", "Magic Missile", "Shield"],
        "languages": ["common"],
        "spell_slots": {"1": 0},
        "feature_choices": {},
        "classes": [{"class_name": "wizard", "level": 1}],
    }


def _live_rogue() -> dict:
    """QA Rogue 910d9c4c: Common / Thieves' Cant / Elvish, origin languages still missing."""
    return {
        "id": "910d9c4c",
        "name": "QA Rogue",
        "species": "halfling",
        "class_name": "rogue",
        "level": 1,
        "background": "criminal",
        "origin_feat": "Alert",
        "ability_scores": {"str": 12, "dex": 15, "con": 13, "int": 14, "wis": 10, "cha": 8},
        "ability_scores_set": True,
        "hp": 10,
        "max_hp": 10,
        "ac": 13,
        "languages": ["common", "thieves' cant", "elvish"],
        "feature_choices": {"thieves_cant_language": "elvish"},
        "classes": [{"class_name": "rogue", "level": 1}],
    }


def _live_paladin() -> dict:
    """QA Paladin c5baf24a: Common only, missing origin languages and gaming set."""
    return {
        "id": "c5baf24a",
        "name": "QA Paladin",
        "species": "dwarf",
        "class_name": "paladin",
        "level": 1,
        "background": "soldier",
        "origin_feat": "Savage Attacker",
        "ability_scores": {"str": 15, "dex": 10, "con": 14, "int": 8, "wis": 12, "cha": 13},
        "ability_scores_set": True,
        "hp": 12,
        "max_hp": 12,
        "ac": 16,
        "languages": ["common"],
        "tool_proficiencies": ["gaming set"],
        "feature_choices": {},
        "classes": [{"class_name": "paladin", "level": 1}],
    }


def test_live_wizard_migrate_fills_2024_picks_and_six_unique_spells():
    char = character_from_dict(_live_wizard())
    assert migrate_legacy_sheet(char) is True
    rebuilt = rebuild_character(char)
    missing = " | ".join(validate_creation_choices(rebuilt))
    assert "origin languages" not in missing.lower()
    assert "elven lineage" not in missing.lower()
    assert "keen senses" not in missing.lower()
    langs = {str(item).lower() for item in rebuilt.languages}
    assert "common" in langs
    assert "elvish" in langs
    book = {str(item).lower() for item in rebuilt.spellbook}
    assert len(book) >= 6
    assert "mage armor" in book
    assert "burning hands" in book or "sleep" in book
    assert not str(rebuilt.feature_choices.get("magic_initiate_level1") or "").strip()
    assert rebuilt.hp == 8
    assert rebuilt.spell_slots["1"] == 0


def test_live_rogue_and_paladin_rebuild_fills_origin_picks():
    rogue = rebuild_character(character_from_dict(_live_rogue()))
    missing_r = " | ".join(validate_creation_choices(rogue)).lower()
    assert "origin languages" not in missing_r
    origin_r = [str(x).lower() for x in rogue.feature_choices.get("origin_languages") or []]
    assert len(origin_r) >= 2
    assert "thieves' cant" in [str(x).lower() for x in rogue.languages]

    paladin = rebuild_character(character_from_dict(_live_paladin()))
    missing_p = " | ".join(validate_creation_choices(paladin)).lower()
    assert "origin languages" not in missing_p
    assert "gaming set" not in missing_p
    assert paladin.feature_choices.get("gaming_set_kind")
    origin_p = [str(x).lower() for x in paladin.feature_choices.get("origin_languages") or []]
    assert "dwarvish" in origin_p


def test_rebuild_persisting_writes_wizard_and_keeps_live_hp():
    data = _live_wizard()
    data["hp"] = 3
    rebuilt = character_to_dict(rebuild_character(character_from_dict(data)))
    merged = preserve_live_resources(data, rebuilt)
    assert merged["hp"] == 3
    assert len({str(s).lower() for s in merged["spellbook"]}) >= 6
    assert merged["feature_choices"].get("elven_lineage")
    assert _migration_fields(data) != _migration_fields(merged)


def test_preserve_live_resources_keeps_mage_armor_ac():
    stored = _live_wizard()
    stored["hp"] = 3
    stored["ac"] = 15
    stored["feature_choices"] = {"_mage_armor_active": True}
    rebuilt = character_to_dict(rebuild_character(character_from_dict(stored)))
    merged = preserve_live_resources(stored, rebuilt)
    assert merged["hp"] == 3
    assert merged["feature_choices"].get("_mage_armor_active") is True
    details = compute_ac_details(character_from_dict(merged))
    assert int(details["computed"]) == 15


def test_magic_initiate_source_of_truth_is_shield_not_mage_armor():
    data = _live_wizard()
    data["feature_choices"] = {
        "magic_initiate_level1": "Shield",
        "magic_initiate_cantrips": ["Minor Illusion", "Acid Splash"],
        "magic_initiate_ability": "int",
    }
    char = rebuild_character(character_from_dict(data))
    assert magic_initiate_spell_name(char).lower() == "shield"
    assert magic_initiate_free_available(char, "Mage Armor", requested_free=True) is False
    assert magic_initiate_free_available(char, "Shield", requested_free=True) is True
    ok, msg = apply_spell_cast(char, "Shield", free_use=True, requested_text="Magic Initiate free")
    assert ok
    assert "no slot" in msg.lower()
    assert char.feature_choices.get("_magic_initiate_free_used") is True
    assert magic_initiate_free_available(char, "Shield", requested_free=True) is False


def test_overlay_prefers_game_hp_ac_hd_from_reconciliation():
    data = _live_wizard()
    narration = (
        "Short rest: not possible, mid-combat. Sheet reconciliation: "
        "auto state HP 8/8, AC 12, HD 0 vs game HP 3/8, AC 15, HD 1. Mage Armor is active."
    )
    updates = overlay_live_resources(data, narration)
    assert updates.get("hp") == 3
    assert updates.get("hit_dice_spent") == 0
    assert updates.get("feature_choices", {}).get("_mage_armor_active") is True
    assert updates.get("ac") == 15


def test_hp_parser_skips_stale_full_hp_when_later_value_differs():
    hp = parse_pc_hp_from_narration(
        "Sheet HP 8/8. The arrow drops you to 3/8 HP.",
        name="QA Wizard",
        max_hp=8,
        current_hp=8,
    )
    assert hp == 3


def test_empty_spell_warning_is_dropped():
    line = "@ 2026-11-19T23:32:27+00:00 ⚠ Spell not on character list: "
    assert is_empty_spell_warning(line)
    assert is_empty_spell_warning("⚠ Spell not on character list:")
    assert not is_empty_spell_warning("⚠ Spell not on character list: Mage Armor")
    cleaned = sanitize_lonelog_content(
        "=> Mott attacks.\n@ 2026-11-19T23:32:27+00:00 ⚠ Spell not on character list: \n=> Mage Armor: Spent level 1 spell slot.\n"
    )
    assert "Spell not on character list:" not in cleaned
    assert "Mage Armor" in cleaned


def test_empty_cast_does_not_log_warning():
    from backend.games.dnd5e.dm.resource_keeper import ResourceTurnUpdates, SpellCast

    char = character_from_dict(_live_wizard())
    entity, logs = apply_resource_updates(char, ResourceTurnUpdates(casts=[SpellCast(spell_name="")]))
    assert entity
    assert not any("spell not on character list" in str(line).lower() for line in logs)


def test_rest_and_cast_skip_continuity_guard():
    assert not _needs_continuity_guard(
        {"shortcut_result": {"task": "short_rest"}, "narrative": "You cannot rest.", "narrative_context": {"canon_summary": "x", "recent_scenes": "y"}}
    )
    assert not _needs_continuity_guard(
        {"shortcut_result": {"task": "cast_spell"}, "narrative": "Mage Armor holds.", "narrative_context": {"canon_summary": "x", "recent_scenes": "y"}}
    )
    assert _needs_continuity_guard(
        {"shortcut_result": {}, "narrative": "You walk into town.", "narrative_context": {"canon_summary": "x", "recent_scenes": "y"}}
    )


def test_character_to_dict_roundtrip_keeps_qa_ids():
    for raw in (_live_wizard(), _live_rogue(), _live_paladin()):
        rebuilt = character_to_dict(rebuild_character(character_from_dict(raw)))
        assert rebuilt["id"] == raw["id"]
        merged = preserve_live_resources(raw, rebuilt)
        assert merged["hp"] == raw["hp"]
