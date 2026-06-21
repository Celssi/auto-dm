"""Creation choice validation and application."""

from backend.characters.character_builder import finalize_new_character
from backend.characters.creation_choices import (
    choices_for_character,
    class_choice_lines,
    species_trait_lines,
    validate_creation_choices,
    weapon_mastery_label,
)
from backend.characters.entity import Dnd5eCharacter
from backend.characters.features import unlocked_features


def _complete_fighter_human(char: Dnd5eCharacter) -> Dnd5eCharacter:
    char.human_skill = "perception"
    char.fighting_style_feat = "defense"
    char.weapon_mastery = ["greatsword", "longsword", "spear"]
    char.versatile_origin_feat = "alert"
    char.feature_choices = {
        "human_skill": "perception",
        "fighting_style_feat": "defense",
        "weapon_mastery": ["greatsword", "longsword", "spear"],
        "versatile_origin_feat": "alert",
    }
    return char


def test_fighter_requires_fighting_style_and_weapon_mastery():
    char = Dnd5eCharacter(
        name="Larry",
        species="human",
        class_name="fighter",
        level=1,
        background="soldier",
    )
    missing = validate_creation_choices(char)
    assert any("Fighting Style" in m for m in missing)
    assert any("Weapon Mastery" in m for m in missing)
    assert any("Skillful" in m for m in missing)


def test_complete_fighter_passes_validation():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry", species="human", class_name="fighter", level=1, background="soldier"
        )
    )
    assert validate_creation_choices(char) == []


def test_apply_adds_human_skill_and_fighting_style_feat():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry",
            species="human",
            class_name="fighter",
            level=1,
            background="soldier",
            class_skill_choices=["athletics", "persuasion"],
            starting_gear_choice="heavy",
            ability_scores={"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 10, "cha": 12},
            ability_scores_set=True,
        )
    )
    built = finalize_new_character(char)
    assert "perception" in built.skill_proficiencies
    assert "Defense" in built.feats
    assert built.weapon_mastery == ["greatsword", "longsword", "spear"]


def test_weapon_mastery_label_includes_property():
    label = weapon_mastery_label("greatsword")
    assert "Greatsword" in label
    assert "Graze" in label


def test_soldier_background_gear_merges_with_fighter():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry",
            species="human",
            class_name="fighter",
            level=1,
            background="soldier",
            class_skill_choices=["athletics", "persuasion"],
            starting_gear_choice="heavy",
            background_gear_choice="kit",
            ability_scores={"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 10, "cha": 12},
            ability_scores_set=True,
        )
    )
    built = finalize_new_character(char)
    inv = [i.lower() for i in built.inventory]
    assert "spear" in inv
    assert built.currency.get("gp") == 18


def test_preview_finalize_rejects_incomplete():
    char = Dnd5eCharacter(
        name="X", species="human", class_name="fighter", level=1, background="soldier"
    )
    missing = validate_creation_choices(char)
    assert len(missing) >= 3


def test_human_species_traits_include_resourceful_and_merged_picks():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry",
            species="human",
            class_name="fighter",
            level=1,
            background="soldier",
            size="medium",
        )
    )
    char.feature_choices["size"] = "medium"
    traits = {t["label"]: t for t in species_trait_lines(char)}
    assert "Resourceful" in traits
    assert "Heroic Inspiration" in traits["Resourceful"]["detail"]
    assert traits["Skillful"]["detail"] == "Perception"
    assert traits["Versatile"]["detail"] == "Alert"
    assert traits["Size"]["detail"] == "Medium"


def test_dwarf_species_traits_are_all_automatic():
    char = Dnd5eCharacter(name="D", species="dwarf", class_name="fighter", level=1)
    traits = species_trait_lines(char)
    labels = [t["label"] for t in traits]
    assert "Darkvision 120 ft." in labels
    assert "Dwarven Resilience" in labels
    assert all(t["automatic"] for t in traits)


def test_class_choices_exclude_species_picks():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry", species="human", class_name="fighter", level=1, background="soldier"
        )
    )
    class_ids = {row["id"] for row in class_choice_lines(char)}
    assert "human_skill" not in class_ids
    assert "versatile_origin_feat" not in class_ids
    assert "fighting_style_feat" in class_ids
    assert "weapon_mastery" in class_ids


def test_initiative_includes_alert_proficiency():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry",
            species="human",
            class_name="fighter",
            level=1,
            background="soldier",
            ability_scores={"str": 17, "dex": 12, "con": 14, "int": 14, "wis": 10, "cha": 8},
        )
    )
    assert char.has_alert_feat()
    assert char.initiative_modifier() == 3  # DEX +1, Alert proficiency +2


def test_elf_wood_elf_lineage_sets_speed():
    char = Dnd5eCharacter(
        name="Leyri",
        species="elf",
        class_name="druid",
        level=1,
        feature_choices={
            "elven_lineage": "wood_elf",
            "keen_senses_skill": "insight",
            "primal_order": "magician",
        },
    )
    built = finalize_new_character(char)
    assert built.speed == 35


def test_unlocked_features_includes_species_traits():
    char = _complete_fighter_human(
        Dnd5eCharacter(
            name="Larry", species="human", class_name="fighter", level=1, background="soldier"
        )
    )
    uf = unlocked_features(char)
    assert any(t["label"] == "Resourceful" for t in uf["species_traits"])
    assert not any(r["id"] == "human_skill" for r in uf["resolved_choices"])


def test_elf_choices_listed():
    char = Dnd5eCharacter(species="elf", class_name="wizard", level=1)
    ids = [c["id"] for c in choices_for_character(char)]
    assert "elven_lineage" in ids
    assert "keen_senses_skill" in ids
