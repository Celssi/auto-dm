"""AC breakdown, equipment display, Second Wind, and shortcut filtering."""

from backend.dm.dice import roll_death_saves
from backend.games.dnd5e.actions import shortcuts_for_character
from backend.games.dnd5e.characters.character_builder import (
    backfill_missing_package_gear,
    rebuild_character,
)
from backend.games.dnd5e.characters.class_resources import (
    compute_ac_details,
    equipment_display_items,
    second_wind_max,
    weapon_mastery_warnings,
)
from backend.games.dnd5e.characters.entity import Dnd5eCharacter, character_to_dict
from backend.glossary import lookup_entry


def _larry() -> Dnd5eCharacter:
    return Dnd5eCharacter(
        name="Larry Swordstein",
        species="human",
        class_name="fighter",
        level=1,
        background="soldier",
        class_skill_choices=["athletics", "persuasion"],
        fighting_style_feat="defense",
        weapon_mastery=["greatsword", "longsword", "spear"],
        origin_feat="savage_attacker",
        versatile_origin_feat="alert",
        starting_gear_choice="heavy",
        armor="chain_mail",
        weapons=[{"name": "Greatsword", "damage": "2d6", "damage_type": "slashing", "ability": "str"}],
        inventory=["Dungeoneer's Pack", "Flail", "Javelins (8)"],
        ability_scores={"str": 17, "dex": 12, "con": 14, "int": 14, "wis": 10, "cha": 8},
        ability_scores_set=True,
    )


def test_defense_chain_mail_ac_is_17():
    details = compute_ac_details(_larry())
    assert details["computed"] == 17
    labels = [p["label"] for p in details["parts"]]
    assert any("chain" in str(p).lower() or "Chain" in str(p) for p in labels)
    assert "Defense" in labels


def test_equipment_lists_armor_and_greatsword():
    items = equipment_display_items(_larry())
    joined = " ".join(items).lower()
    assert "chain" in joined
    assert "greatsword" in joined
    assert "dungeoneer's pack" in joined or "dungeoneers pack" in joined.replace("'", "")


def test_mastery_warning_when_weapon_missing():
    char = _larry()
    char.weapons = []
    warnings = weapon_mastery_warnings(char)
    assert any("greatsword" in w["weapon"].lower() for w in warnings)


def test_second_wind_max_fighter_1():
    assert second_wind_max(_larry()) == 2


def test_shortcuts_hide_cast_spell_and_lucky_for_fighter():
    ids = {row["id"] for row in shortcuts_for_character(
        {
            "class_name": "fighter",
            "level": 1,
            "origin_feat": "savage_attacker",
            "cantrips": [],
            "prepared_spells": [],
            "known_spells": [],
            "spell_slots": {},
        }
    )}
    assert "ability_check" in ids
    assert "second_wind" in ids
    assert "savage_attacker" in ids
    assert "cast_spell" not in ids
    assert "lucky" not in ids
    assert "healer_medic" not in ids


def test_shortcuts_empty_character_keeps_core_only():
    ids = {row["id"] for row in shortcuts_for_character({})}
    assert "ability_check" in ids
    assert "cast_spell" not in ids
    assert "lucky" not in ids
    assert "healer_medic" not in ids
    assert "second_wind" not in ids


def test_backfill_missing_heavy_gear():
    char = Dnd5eCharacter(
        name="Larry",
        class_name="fighter",
        level=1,
        starting_gear_choice="heavy",
        armor="none",
        weapons=[],
        inventory=["Dungeoneer's Pack"],
    )
    filled = backfill_missing_package_gear(char)
    assert filled.armor == "chain_mail"
    assert any(str(w.get("name", "")).lower() == "greatsword" for w in filled.weapons)


def test_rebuild_dict_applies_defense_ac():
    char = Dnd5eCharacter(
        name="Larry",
        species="human",
        class_name="fighter",
        level=1,
        background="soldier",
        fighting_style_feat="defense",
        starting_gear_choice="heavy",
        armor="none",
        inventory=["Dungeoneer's Pack"],
        ability_scores={"str": 17, "dex": 12, "con": 14, "int": 14, "wis": 10, "cha": 8},
        ability_scores_set=True,
    )
    data = character_to_dict(rebuild_character(char))
    assert data["armor"] == "chain_mail"
    assert data["ac"] == 17


def test_death_save_summary_has_no_question_mark_placeholder():
    result = roll_death_saves(pre_rolled=12)
    assert "?" not in result["summary"]
    assert "success" in result["summary"]


def test_system_prompt_is_2024_only():
    from backend.games.dnd5e.prompts import dnd5e_stable_system_prompt

    text = dnd5e_stable_system_prompt()
    lower = text.lower()
    assert "d&d 5e (2024)" in lower
    assert "never apply 2014" in lower
    assert "2014 fallback" in lower


def test_weapon_glossary_has_no_em_dash():
    hit = lookup_entry("greatsword", use_rag=False)
    summary = hit.get("summary") or ""
    assert "\u2014" not in summary
    assert "\u2013" not in summary
