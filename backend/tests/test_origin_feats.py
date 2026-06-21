"""PHB 2024 origin feat normalization and mechanical hooks."""

from backend.games.dnd5e.characters.character_builder import compute_max_hp, rebuild_character
from backend.games.dnd5e.characters.creation_choices import (
    apply_creation_choices,
    choices_for_character,
    validate_creation_choices,
)
from backend.games.dnd5e.characters.entity import Dnd5eCharacter
from backend.games.dnd5e.characters.features import unlocked_features
from backend.games.dnd5e.characters.origin_feats import (
    ORIGIN_FEAT_LABELS,
    ORIGIN_FEAT_PASSIVES,
    apply_origin_feat_proficiencies,
    feat_matches_when_list,
    has_origin_feat,
    luck_points_max,
    normalize_origin_feat_id,
    origin_feat_ids,
    origin_feat_passive_lines,
    tough_hp_bonus,
)


def _fighter(level: int = 1, **kwargs) -> Dnd5eCharacter:
    base = dict(
        name="Test",
        species="human",
        class_name="fighter",
        level=level,
        background="soldier",
        ability_scores={"str": 15, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 8},
        ability_scores_set=True,
        class_skill_choices=["athletics", "intimidation"],
        starting_gear_choice="heavy",
    )
    base.update(kwargs)
    return Dnd5eCharacter(**base)


def test_all_origin_feats_have_labels_and_passives():
    assert set(ORIGIN_FEAT_LABELS) == set(ORIGIN_FEAT_PASSIVES)
    assert len(ORIGIN_FEAT_LABELS) == 12


def test_normalize_origin_feat_id_accepts_labels_and_ids():
    assert normalize_origin_feat_id("Alert") == "alert"
    assert normalize_origin_feat_id("alert") == "alert"
    assert normalize_origin_feat_id("Magic Initiate (Wizard)") == "magic_initiate_wizard"
    assert normalize_origin_feat_id("magic_initiate_cleric") == "magic_initiate_cleric"
    assert normalize_origin_feat_id("Tavern Brawler") == "tavern_brawler"


def test_origin_feat_ids_includes_background_and_versatile():
    char = _fighter(origin_feat="Healer", versatile_origin_feat="alert")
    assert origin_feat_ids(char) == {"healer", "alert"}


def test_feat_matches_when_list_accepts_label_or_id():
    char = _fighter(versatile_origin_feat="Skilled")
    assert feat_matches_when_list(["Skilled", "skilled"], char)
    char.origin_feat = "Magic Initiate (Druid)"
    assert feat_matches_when_list(["magic_initiate_druid"], char)


def test_alert_initiative_bonus():
    char = _fighter(
        versatile_origin_feat="alert",
        ability_scores={"str": 15, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 8},
    )
    assert char.initiative_modifier() == 3  # DEX +1, Alert +2 PB


def test_tough_adds_hp_per_level():
    char = _fighter(level=3, origin_feat="tough")
    assert tough_hp_bonus(char) == 6
    rebuilt = rebuild_character(char)
    assert rebuilt.max_hp == compute_max_hp(rebuilt)
    assert rebuilt.max_hp >= 6 + 10  # at least base HP + Tough bonus


def test_lucky_points_equal_proficiency_bonus():
    char = _fighter(level=5, origin_feat="lucky")
    assert luck_points_max(char) == 3


def test_tavern_brawler_grants_improvised_weapon_proficiency():
    char = _fighter(origin_feat="tavern_brawler")
    apply_origin_feat_proficiencies(char)
    assert "improvised_weapons" in char.tool_proficiencies


def test_skilled_subchoice_applies_skill_proficiencies():
    char = _fighter(
        origin_feat="skilled",
        feature_choices={"skilled_proficiencies": ["arcana", "history", "religion"]},
    )
    apply_creation_choices(char)
    for sk in ("arcana", "history", "religion"):
        assert sk in char.skill_proficiencies


def test_crafter_subchoice_applies_tool_proficiencies():
    char = _fighter(
        origin_feat="crafter",
        feature_choices={"crafter_tools": ["smiths_tools", "tinkers_tools", "woodcarvers_tools"]},
    )
    apply_creation_choices(char)
    for tool in ("smiths_tools", "tinkers_tools", "woodcarvers_tools"):
        assert tool in char.tool_proficiencies


def test_musician_subchoice_applies_instrument_proficiencies():
    char = _fighter(
        origin_feat="musician",
        feature_choices={"musician_instruments": ["lute", "flute", "drum"]},
    )
    apply_creation_choices(char)
    for inst in ("lute", "flute", "drum"):
        assert inst in char.tool_proficiencies


def test_magic_initiate_subchoices_apply_spells():
    char = _fighter(
        origin_feat="magic_initiate_wizard",
        feature_choices={
            "magic_initiate_cantrips": ["fire_bolt", "mending"],
            "magic_initiate_level1": "shield",
        },
    )
    apply_creation_choices(char)
    assert "fire_bolt" in char.cantrips or "Fire Bolt" in char.cantrips
    assert any("shield" in s.lower() for s in char.known_spells)


def test_skilled_requires_three_proficiencies():
    char = _fighter(origin_feat="skilled", feature_choices={"skilled_proficiencies": ["arcana"]})
    missing = validate_creation_choices(char)
    assert any("Skilled" in m for m in missing)
    char.feature_choices = {"skilled_proficiencies": ["arcana", "history", "religion"]}
    assert validate_creation_choices(char) == [] or not any(
        "Skilled" in m for m in validate_creation_choices(char)
    )


def test_origin_feat_passive_lines_cover_active_feats():
    char = _fighter(origin_feat="healer", versatile_origin_feat="lucky")
    lines = origin_feat_passive_lines(char)
    feats = {row["feat_id"] for row in lines}
    assert feats == {"healer", "lucky"}
    unlocked = unlocked_features(char)
    assert unlocked["origin_feat_effects"] == lines


def test_has_origin_feat_for_all_canonical_ids():
    for fid in ORIGIN_FEAT_LABELS:
        char = _fighter(origin_feat=fid)
        assert has_origin_feat(char, fid)
        assert fid in origin_feat_ids(char)


def test_skilled_subchoices_appear_when_stored_as_label():
    char = _fighter(origin_feat="Skilled")
    choice_ids = {c["id"] for c in choices_for_character(char)}
    assert "skilled_proficiencies" in choice_ids
