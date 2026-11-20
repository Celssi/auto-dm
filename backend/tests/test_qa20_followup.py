"""Follow-up QA after #19/#20: rest HD, refused recast, Sage MI, dead NPCs, bootstrap speed."""

from backend.dm.story_director import parse_outline_to_progress_heuristic
from backend.dm.world_context import npc_is_dead
from backend.games.dnd5e.characters.character_builder import apply_short_rest, rebuild_character
from backend.games.dnd5e.characters.creation_choices import choices_for_character
from backend.games.dnd5e.characters.entity import character_from_dict, character_to_dict
from backend.games.dnd5e.characters.origin_feats import origin_feat_ids
from backend.games.dnd5e.characters.spell_resources import apply_spell_cast
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_cast,
    apply_pending_rest,
    cast_refused,
    no_hit_dice_requested,
)
from backend.games.registry import preserve_live_resources


def _sage_wizard(**overrides) -> dict:
    data = {
        "name": "QA Sage 3",
        "species": "human",
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
        "hit_die": 6,
        "hit_dice_max": 1,
        "hit_dice_spent": 0,
        "cantrips": ["Fire Bolt", "Mage Hand", "Prestidigitation"],
        "prepared_spells": ["Detect Magic", "Mage Armor", "Magic Missile", "Shield"],
        "spellbook": ["Detect Magic", "Mage Armor", "Magic Missile", "Shield", "Sleep", "Burning Hands"],
        "spell_slots": {"1": 2},
        "feature_choices": {
            "human_skill": "perception",
            "magic_initiate_cantrips": ["Light", "Message"],
            "magic_initiate_level1": "Shield",
            "magic_initiate_ability": "int",
        },
        "classes": [{"class_name": "wizard", "level": 1}],
    }
    data.update(overrides)
    return data


def test_short_rest_at_full_hp_does_not_spend_hit_dice():
    char = character_from_dict(_sage_wizard(hp=8, max_hp=8, hit_dice_spent=0))
    rest = apply_short_rest(char, dice_to_spend=1)
    assert char.hit_dice_spent == 0
    assert char.hp == 8
    assert "Spent" not in (rest.get("summary") or "")


def test_pending_rest_ignores_stale_hp_and_no_hit_dice_text():
    data = _sage_wizard(hp=3, max_hp=8, hit_dice_spent=0)
    dm = (
        "You sit for an hour. You are already at 8 HP, so no Hit Dice are needed. "
        "Arcane Recovery restores a 1st-level slot."
    )
    assert no_hit_dice_requested("I take a short rest", dm)
    updates, logs = apply_pending_rest(
        data,
        {"kind": "short", "dice_to_spend": 1},
        dm,
        user_message="I take a short rest",
    )
    assert updates.get("hit_dice_spent") in (None, 0)
    assert updates.get("hp") in (None, 8)
    assert not any("Spent" in line for line in logs)


def test_refused_mage_armor_recast_does_not_spend_slot():
    data = _sage_wizard()
    data["feature_choices"] = {
        **data["feature_choices"],
        "_mage_armor_active": True,
    }
    data["ac"] = 15
    data["spell_slots"] = {"1": 2}
    dm = "Mage Armor is already active. The ward still holds, so no slot is spent."
    assert cast_refused(dm)
    updates, logs = apply_pending_cast(
        data,
        {"spell_name": "Mage Armor", "slot_level": 1},
        dm,
    )
    assert updates == {}
    assert any("refused" in line.lower() for line in logs)

    char = character_from_dict(data)
    ok, msg = apply_spell_cast(char, "Mage Armor")
    assert ok is False
    assert char.spell_slots["1"] == 2
    assert "already active" in msg.lower()


def test_granted_mage_armor_cast_still_spends_after_pending():
    data = _sage_wizard(spell_slots={"1": 2})
    updates, logs = apply_pending_cast(
        data,
        {"spell_name": "Mage Armor", "slot_level": 1},
        "A shimmering ward settles over you. AC 15.",
    )
    assert updates.get("spell_slots", {}).get("1") == 1
    assert updates.get("ac") == 15
    assert any("Mage Armor" in line for line in logs)


def test_sage_without_origin_feat_field_still_gets_magic_initiate_picks():
    char = character_from_dict(
        {
            "name": "QA Sage 3",
            "species": "human",
            "class_name": "wizard",
            "level": 1,
            "background": "sage",
            "origin_feat": "",
            "ability_scores_set": True,
            "ability_scores": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        }
    )
    assert "magic_initiate_wizard" in origin_feat_ids(char)
    ids = {row["id"] for row in choices_for_character(char)}
    assert "magic_initiate_cantrips" in ids
    assert "magic_initiate_level1" in ids
    assert "magic_initiate_ability" in ids


def test_rebuild_dedupes_magic_initiate_feat_list():
    data = _sage_wizard()
    data["feats"] = ["Magic Initiate (Wizard)", "Magic Initiate (Wizard)", "Magic Initiate"]
    rebuilt = rebuild_character(character_from_dict(data))
    labels = [str(f).lower() for f in rebuilt.feats]
    assert not any("magic initiate" in f for f in labels)
    assert rebuilt.origin_feat.lower().startswith("magic initiate")


def test_review_rebuild_uses_base_ability_scores():
    data = {
        "name": "QA Sage 3",
        "species": "human",
        "class_name": "wizard",
        "level": 1,
        "background": "sage",
        "ability_scores_set": False,
        "ability_scores": {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10},
        "base_ability_scores": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        "hp": 0,
        "max_hp": 0,
        "feature_choices": {"human_skill": "perception", "origin_languages": ["elvish", "draconic"]},
    }
    rebuilt = rebuild_character(character_from_dict(data), recompute_hp=False)
    assert rebuilt.ability_scores["int"] >= 15
    assert rebuilt.max_hp >= 6
    assert rebuilt.hp == rebuilt.max_hp


def test_dead_npc_is_not_treated_as_alive():
    assert npc_is_dead({"name": "Motti", "status": "dead"})
    assert npc_is_dead({"name": "Motti", "body": "Motti was killed in the alley."})
    assert not npc_is_dead({"name": "Motti", "body": "A living merchant in the square."})


def test_character_dict_for_dm_keeps_live_ac_and_hit_dice():
    stored = _sage_wizard(ac=15, hit_dice_spent=1)
    stored["feature_choices"] = {
        **stored["feature_choices"],
        "_mage_armor_active": True,
    }
    rebuilt = character_to_dict(rebuild_character(character_from_dict(stored)))
    dm = preserve_live_resources(stored, rebuilt)
    assert dm["ac"] == 15
    assert dm["hit_dice_spent"] == 1
    assert (dm.get("feature_choices") or {}).get("_mage_armor_active") is True


def test_narrator_builds_context_from_live_sheet():
    import inspect

    from backend.games.dnd5e.dm.agents.nodes import narrator_dm_node

    source = inspect.getsource(narrator_dm_node)
    assert "character_dict_for_dm" in source


def test_outline_heuristic_skips_extra_llm():
    outline = (
        "## Premise\nA haunted mill.\n\n"
        "## Act 1\nThe miller is missing.\n\n"
        "## Rising action\nTracks lead to the cellar.\n\n"
        "## Climax\nThe spirit must be laid to rest.\n"
    )
    progress = parse_outline_to_progress_heuristic(outline)
    assert progress is not None
    assert len(progress.checkpoints) >= 3
    assert progress.checkpoints[0].status == "active"
