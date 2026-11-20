"""QA 2024 character-creation and play-resource regressions."""

from backend.games.dnd5e.characters.character_builder import (
    apply_background_asi,
    apply_short_rest,
    compute_max_hp,
    finalize_new_character,
    highest_spell_slot_level,
    long_rest_recover,
    rebuild_character,
)
from backend.games.dnd5e.characters.class_resources import (
    equipment_display_items,
    lay_on_hands_max,
    mastery_weapons_for_class,
    merge_counted_labels,
    sneak_attack_dice,
    weapon_attack_details,
)
from backend.games.dnd5e.characters.creation_choices import choices_for_character
from backend.games.dnd5e.characters.entity import Dnd5eCharacter, character_from_dict
from backend.games.dnd5e.dm.combat_manager import (
    SHIELD_AC_BONUS,
    resolve_pending_reaction,
)
from backend.dm.encounters import CombatState


def _wizard(**kwargs) -> Dnd5eCharacter:
    base = dict(
        name="QA Wizard",
        species="elf",
        class_name="wizard",
        level=1,
        background="sage",
        origin_feat="Magic Initiate (Wizard)",
        ability_scores={"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        base_ability_scores={"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        ability_scores_set=True,
        background_asi_plus2="int",
        background_asi_plus1="con",
        class_skill_choices=["insight", "investigation"],
        cantrips=["Fire Bolt", "Mage Hand", "Ray of Frost"],
        spellbook=[
            "Detect Magic",
            "Mage Armor",
            "Magic Missile",
            "Shield",
            "Burning Hands",
            "Sleep",
        ],
        prepared_spells=["Detect Magic", "Mage Armor", "Magic Missile", "Shield"],
        starting_gear_choice="standard",
        background_gear_choice="kit",
        feature_choices={
            "elven_lineage": "high_elf",
            "keen_senses_skill": "perception",
            "high_elf_spell_ability": "int",
            "origin_languages": ["elvish", "draconic"],
            "magic_initiate_cantrips": ["Minor Illusion", "Acid Splash"],
            "magic_initiate_level1": "Find Familiar",
            "magic_initiate_ability": "int",
        },
    )
    base.update(kwargs)
    return Dnd5eCharacter(**base)


def _rogue(**kwargs) -> Dnd5eCharacter:
    base = dict(
        name="QA Rogue",
        species="halfling",
        class_name="rogue",
        level=1,
        background="criminal",
        origin_feat="Alert",
        ability_scores={"str": 12, "dex": 15, "con": 13, "int": 14, "wis": 10, "cha": 8},
        base_ability_scores={"str": 12, "dex": 15, "con": 13, "int": 14, "wis": 10, "cha": 8},
        ability_scores_set=True,
        background_asi_plus2="dex",
        background_asi_plus1="con",
        class_skill_choices=["acrobatics", "insight", "investigation", "perception"],
        weapon_mastery=["dagger", "shortsword"],
        starting_gear_choice="standard",
        background_gear_choice="kit",
        feature_choices={
            "rogue_expertise": ["stealth", "perception"],
            "thieves_cant_language": "elvish",
            "origin_languages": ["halfling", "orc"],
            "weapon_mastery": ["dagger", "shortsword"],
        },
    )
    base.update(kwargs)
    return Dnd5eCharacter(**base)


def _paladin(**kwargs) -> Dnd5eCharacter:
    base = dict(
        name="QA Paladin",
        species="dwarf",
        class_name="paladin",
        level=1,
        background="soldier",
        origin_feat="Savage Attacker",
        ability_scores={"str": 15, "dex": 10, "con": 13, "int": 8, "wis": 12, "cha": 14},
        base_ability_scores={"str": 15, "dex": 10, "con": 13, "int": 8, "wis": 12, "cha": 14},
        ability_scores_set=True,
        background_asi_plus2="str",
        background_asi_plus1="dex",
        class_skill_choices=["insight", "persuasion"],
        prepared_spells=["Bless", "Cure Wounds"],
        weapon_mastery=["longsword", "warhammer"],
        starting_gear_choice="standard",
        background_gear_choice="kit",
        feature_choices={
            "origin_languages": ["dwarvish", "giant"],
            "gaming_set_kind": "dice_set",
            "weapon_mastery": ["longsword", "warhammer"],
        },
    )
    base.update(kwargs)
    return Dnd5eCharacter(**base)


def test_background_asi_plus2_int_plus1_con():
    scores = apply_background_asi(
        {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        "sage",
        plus2="int",
        plus1="con",
    )
    assert scores["int"] == 17
    assert scores["con"] == 14


def test_background_asi_all_three():
    scores = apply_background_asi(
        {"str": 15, "dex": 10, "con": 13, "int": 8, "wis": 12, "cha": 14},
        "soldier",
        all_three=True,
    )
    assert scores["str"] == 16
    assert scores["dex"] == 11
    assert scores["con"] == 14


def test_wizard_spellbook_and_high_elf_cantrip():
    char = finalize_new_character(_wizard())
    assert len(char.spellbook) == 6
    cantrips = [str(name).lower() for name in char.cantrips]
    assert "prestidigitation" in cantrips
    assert cantrips.count("prestidigitation") == 1
    assert highest_spell_slot_level(char) == 1
    ids = {c["id"] for c in choices_for_character(char)}
    assert "high_elf_spell_ability" in ids


def test_rogue_expertise_doubles_pb_and_thieves_cant():
    char = finalize_new_character(_rogue())
    assert "stealth" in char.expertise_skills()
    assert "perception" in char.expertise_skills()
    assert char.skill_bonus_value("stealth", "dex") == 7
    assert char.skill_bonus_value("perception", "wis") == 4
    assert char.passive_perception() == 14
    langs = [lang.lower() for lang in char.languages]
    assert "common" in langs
    assert "thieves' cant" in langs
    assert "elvish" in langs
    assert sneak_attack_dice(char) == 1


def test_dwarven_toughness_and_lay_on_hands():
    char = finalize_new_character(_paladin())
    assert compute_max_hp(char) == 12
    assert char.max_hp == 12
    assert lay_on_hands_max(char) == 5
    assert char.lay_on_hands_remaining == 5
    existing = character_from_dict(
        {
            "name": "Old Dwarf",
            "species": "dwarf",
            "class_name": "paladin",
            "level": 1,
            "background": "soldier",
            "ability_scores": {"str": 17, "dex": 11, "con": 13, "int": 8, "wis": 12, "cha": 14},
            "ability_scores_set": True,
            "max_hp": 11,
            "hp": 11,
            "hit_die": 10,
        }
    )
    rebuilt = rebuild_character(existing)
    assert rebuilt.max_hp == 12
    assert rebuilt.hp == 12


def test_arcane_recovery_on_short_rest():
    char = finalize_new_character(_wizard())
    char.spell_slots = {"1": 0}
    char.hp = char.max_hp
    rest = apply_short_rest(char, dice_to_spend=0)
    assert char.spell_slots["1"] == 1
    assert "Arcane Recovery" in rest["summary"]
    apply_short_rest(char, dice_to_spend=0)
    assert char.spell_slots["1"] == 1
    long_rest_recover(char)
    assert char.spell_slots["1"] == 2


def test_short_rest_spends_hit_die_when_hurt():
    char = finalize_new_character(_wizard())
    char.hp = max(1, char.max_hp - 4)
    rest = apply_short_rest(char, dice_to_spend=1)
    assert char.hit_dice_spent == 1
    assert "d" in rest["summary"]


def test_gear_stacks_and_hides_armor_duplicate():
    merged = merge_counted_labels(["Dagger (2)", "Robe"], ["Dagger (2)", "Robe"])
    assert "Dagger (4)" in merged
    assert "Robe (2)" in merged
    char = finalize_new_character(_rogue())
    display = [item.lower() for item in equipment_display_items(char)]
    leather = [item for item in display if "leather" in item]
    assert len(leather) == 1


def test_mastery_weapon_lists_and_attack_math():
    rogue_ids = {row["id"] for row in mastery_weapons_for_class("rogue")}
    assert "dagger" in rogue_ids
    assert "longsword" not in rogue_ids
    assert mastery_weapons_for_class("wizard") == []
    char = finalize_new_character(_rogue())
    lines = weapon_attack_details(char)
    names = {row["name"].lower(): row for row in lines}
    assert "shortsword" in names
    assert names["shortsword"]["attack"] == 5


def test_rules_referee_skips_rag_without_needs_rules():
    from backend.games.dnd5e.dm.agents.nodes import _needs_rules_check, rules_referee_node

    result = rules_referee_node({"needs_rules": False, "user_message": "I look around."})
    assert result.get("rules_context") == ""
    assert _needs_rules_check("I cast Fire Bolt at the goblin lookout") is False
    assert _needs_rules_check("How does Shield work as a reaction?") is True


def test_combat_post_applies_damage_for_cast_spell(monkeypatch):
    from backend.dm.encounters import CombatState
    from backend.games.dnd5e.dm.agents import nodes as agents

    combat = CombatState(encounter_id="e1", encounter_name="Snik", status="active")
    called = {}

    monkeypatch.setattr(agents, "load_combat_state", lambda _sid: combat)

    def fake_finish(_sid, char_dict):
        called["ran"] = True
        updated = dict(char_dict)
        updated["hp"] = 3
        return combat, updated, ["Lookout hits for 5."]

    monkeypatch.setattr(agents, "finish_player_turn", fake_finish)
    monkeypatch.setattr("backend.storage.save_character", lambda *_args, **_kwargs: None)
    result = agents.combat_manager_post_node(
        {
            "session_id": "s1",
            "user_message": "I stamp out the flame and bind Snik.",
            "character": {"id": "c1", "hp": 8, "max_hp": 8},
        }
    )
    assert called.get("ran") is True
    assert result["character"]["hp"] == 3


def test_shield_reaction_negates_hit_below_ac_plus_five():
    from backend.games.dnd5e.characters.entity import character_to_dict

    state = CombatState(encounter_id="e1", encounter_name="Snik")
    state.pending_reaction = {
        "type": "shield",
        "attacker": "Snik",
        "damage": 5,
        "attack_total": 14,
        "target_ac": 12,
    }
    char = finalize_new_character(_wizard())
    char.prepared_spells = ["Shield"]
    char.spell_slots = {"1": 2}
    data = character_to_dict(char)
    _, updated, events = resolve_pending_reaction(state, data, "I cast Shield")
    assert "Shield" in events[0]
    assert updated["spell_slots"]["1"] == 1
    assert updated["hp"] == char.hp
    assert SHIELD_AC_BONUS == 5
