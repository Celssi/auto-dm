"""Starting equipment packages."""

from backend.characters.character_builder import finalize_new_character
from backend.characters.character_data import list_starting_gear_options
from backend.characters.entity import Dnd5eCharacter, character_to_dict


def test_fighter_starting_gear_has_no_gold_only_option():
    opts = list_starting_gear_options("fighter")
    assert len(opts) == 2
    assert {o["id"] for o in opts} == {"heavy", "skirmisher"}


def test_preview_merges_class_and_background_skills():
    char = Dnd5eCharacter(
        name="Larry",
        species="human",
        class_name="fighter",
        level=1,
        background="soldier",
        class_skill_choices=["athletics", "persuasion"],
        human_skill="perception",
        fighting_style_feat="defense",
        weapon_mastery=["greatsword", "longsword", "spear"],
        versatile_origin_feat="alert",
        feature_choices={
            "human_skill": "perception",
            "fighting_style_feat": "defense",
            "weapon_mastery": ["greatsword", "longsword", "spear"],
            "versatile_origin_feat": "alert",
        },
        starting_gear_choice="heavy",
        background_gear_choice="kit",
        ability_scores={"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 10, "cha": 12},
        ability_scores_set=True,
    )
    built = finalize_new_character(char)
    data = character_to_dict(built)
    skills = set(data["skill_proficiencies"])
    assert "athletics" in skills
    assert "persuasion" in skills
    assert "intimidation" in skills
    assert "perception" in skills
    assert set(data["save_proficiencies"]) == {"str", "con"}
    assert data["hit_die"] == 10
    assert data["armor"] == "chain_mail"
    assert "Greatsword" in [w["name"] for w in data["weapons"]]
    assert "Defense" in data["feats"]
    assert data["currency"]["gp"] == 18


def test_skirmisher_starting_gear_choice():
    char = Dnd5eCharacter(
        name="Archer",
        species="human",
        class_name="fighter",
        level=1,
        background="soldier",
        class_skill_choices=["athletics", "persuasion"],
        starting_gear_choice="skirmisher",
        ability_scores={"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 10, "cha": 12},
        ability_scores_set=True,
    )
    built = finalize_new_character(char)
    data = character_to_dict(built)
    assert data["armor"] == "studded_leather"
    assert data["shield"] is False
    inv = [i.lower() for i in data["inventory"]]
    assert "longbow" in inv
