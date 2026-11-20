"""QA of #22: final-narration HP/conditions, rest grant, rest log HP."""

from backend.games.dnd5e.characters.character_builder import short_rest_heal
from backend.games.dnd5e.characters.entity import character_from_dict
from backend.games.dnd5e.dm.agents.nodes import resource_keeper_node
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_rest,
    narrative_short_rest_detected,
    overlay_live_resources,
    parse_conditions_from_narration,
    parse_pc_hp_from_narration,
    rest_granted,
)


def _sage(*, hp: int = 8, hit_dice_spent: int = 0) -> dict:
    return {
        "id": "51e929c7",
        "name": "QA Sage 4",
        "species": "human",
        "class_name": "wizard",
        "level": 1,
        "background": "sage",
        "ability_scores": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
        "ability_scores_set": True,
        "hp": hp,
        "max_hp": 8,
        "ac": 15,
        "hit_die": 6,
        "hit_dice_max": 1,
        "hit_dice_spent": hit_dice_spent,
        "conditions": [],
        "prepared_spells": ["Mage Armor", "Shield"],
        "spell_slots": {"1": 1},
        "feature_choices": {"_mage_armor_active": True},
        "classes": [{"class_name": "wizard", "level": 1}],
    }


def test_fall_final_equals_stream_applies_hp_and_prone():
    text = "Falling: 1d6 = 3. HP 8 -> 5/8, Prone"
    assert parse_pc_hp_from_narration(text, name="QA Sage 4", max_hp=8, current_hp=8) == 5
    assert "Prone" in parse_conditions_from_narration(text, [])
    result = resource_keeper_node(
        {
            "character": _sage(hp=8),
            "response": text,
            "user_message": "I drop from the balcony.",
            "shortcut_result": {},
        }
    )
    updates = result.get("character_updates") or {}
    assert updates.get("hp") == 5
    assert "Prone" in (updates.get("conditions") or [])
    logs = " ".join(result.get("resource_log") or [])
    assert "damage" in logs.lower()
    assert "5/8" in logs


def test_fall_final_rewrite_does_not_apply_streamed_damage():
    final = "The stairs hold. You keep your footing and take no fall."
    result = resource_keeper_node(
        {
            "character": _sage(hp=8),
            "response": final,
            "narrative": final,
            "user_message": "I drop from the balcony.",
            "shortcut_result": {},
        }
    )
    updates = result.get("character_updates") or {}
    assert updates.get("hp") is None
    assert "Prone" not in (updates.get("conditions") or [])
    logs = " ".join(result.get("resource_log") or [])
    assert "damage" not in logs.lower()


def test_fall_text_is_not_a_short_rest():
    text = "Falling: 1d6 = 3. HP 8 -> 5/8, Prone. You recover your breath."
    assert not rest_granted(text, kind="short")
    assert not narrative_short_rest_detected("I drop from the balcony.", text)
    overlay = overlay_live_resources(_sage(hp=8), text)
    assert overlay.get("hp") == 5


def test_short_rest_heal_log_uses_start_hp():
    char = character_from_dict(_sage(hp=4, hit_dice_spent=0))
    heal = short_rest_heal(char, dice_to_spend=1)
    summary = str(heal.get("summary") or "")
    assert "(4 -> " in summary
    assert "(2 -> " not in summary


def test_pending_rest_still_grants_on_hit_die_spent():
    dm = "Hit Die spent, 4/8 -> 8/8. You catch your breath."
    assert rest_granted(dm, kind="short")
    updates, logs = apply_pending_rest(
        _sage(hp=4),
        {"kind": "short", "dice_to_spend": 1},
        dm,
        user_message="**Short rest**",
    )
    assert updates.get("hit_dice_spent") == 1
    assert not any("did not grant" in line.lower() for line in logs)
