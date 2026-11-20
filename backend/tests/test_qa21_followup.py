"""QA of #21: rest grant, final-narrative mechanics, cast intercept, MI free picker."""

from backend.games.dnd5e.characters.entity import character_from_dict
from backend.games.dnd5e.dm.agents.nodes import detect_dnd_shortcut
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_rest,
    overlay_live_resources,
    parse_hit_dice_to_spend,
    parse_pc_hp_from_narration,
    rest_granted,
    rest_refused,
)
from backend.games.dnd5e.dm.spell_autocomplete import extract_cast_query


def _sage(*, hp: int = 4, hit_dice_spent: int = 0) -> dict:
    return {
        "name": "QA Sage 4",
        "species": "human",
        "class_name": "wizard",
        "level": 1,
        "background": "sage",
        "origin_feat": "Magic Initiate (Wizard)",
        "ability_scores": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        "ability_scores_set": True,
        "hp": hp,
        "max_hp": 8,
        "ac": 15,
        "armor": "none",
        "hit_die": 6,
        "hit_dice_max": 1,
        "hit_dice_spent": hit_dice_spent,
        "cantrips": ["Fire Bolt", "Mage Hand", "Prestidigitation"],
        "prepared_spells": ["Detect Magic", "Mage Armor", "Magic Missile", "Shield"],
        "spell_slots": {"1": 1},
        "feature_choices": {
            "_mage_armor_active": True,
            "magic_initiate_cantrips": ["Light", "Message"],
            "magic_initiate_level1": "Shield",
            "magic_initiate_ability": "int",
        },
        "classes": [{"class_name": "wizard", "level": 1}],
    }


def test_hit_die_spent_narration_grants_short_rest():
    dm = "Hit Die spent, 4/8 -> 8/8. You catch your breath."
    assert not rest_refused(dm)
    assert rest_granted(dm, kind="short")
    assert parse_hit_dice_to_spend("**Short rest**", dm) == 1
    updates, logs = apply_pending_rest(
        _sage(hp=4),
        {"kind": "short", "dice_to_spend": 1},
        dm,
        user_message="**Short rest**",
    )
    assert updates.get("hit_dice_spent") == 1
    assert updates.get("hp", 4) > 4
    assert not any("did not grant" in line.lower() for line in logs)


def test_refused_rest_still_blocked():
    dm = "Short rest: not possible. An enemy is approaching."
    assert rest_refused(dm)
    updates, logs = apply_pending_rest(
        _sage(hp=4),
        {"kind": "short", "dice_to_spend": 1},
        dm,
    )
    assert updates == {}
    assert any("refused" in line.lower() or "not applied" in line.lower() for line in logs)


def test_fall_hp_arrow_is_parsed_and_logged_as_damage():
    text = "1d6 = 4, HP 8 -> 4/8, Prone"
    assert parse_pc_hp_from_narration(text, name="QA Sage 4", max_hp=8, current_hp=8) == 4
    updates = overlay_live_resources(_sage(hp=8), text)
    assert updates.get("hp") == 4
    assert any("damage" in line.lower() for line in updates.get("_logs") or [])


def test_final_stairs_held_does_not_apply_streamed_fall():
    draft = "1d6 = 4, HP 8 -> 4/8, Prone"
    final = "The stairs hold. You keep your footing and take no fall."
    assert parse_pc_hp_from_narration(draft, name="QA Sage 4", max_hp=8, current_hp=8) == 4
    updates = overlay_live_resources(_sage(hp=8), final)
    assert updates.get("hp") is None
    assert not any("damage" in line.lower() for line in updates.get("_logs") or [])


def test_cancel_recast_is_not_a_spell_command():
    text = "No, cancel that recast. Do not cast anything."
    assert extract_cast_query(text) is None
    assert detect_dnd_shortcut(text, _sage()) is None


def test_magic_initiate_shield_stays_on_sheet_for_free_use():
    char = character_from_dict(_sage())
    fc = char.feature_choices or {}
    assert str(fc.get("magic_initiate_level1") or "").lower() == "shield"
    assert "shield" in [s.lower() for s in char.prepared_spells]
