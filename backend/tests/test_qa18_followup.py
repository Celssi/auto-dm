"""QA of PR #18 remaining bugs: rest in combat, HP, bare cast, Magic Initiate."""

from backend.games.dnd5e.characters.character_builder import rebuild_character
from backend.games.dnd5e.characters.class_resources import compute_ac_details
from backend.games.dnd5e.characters.creation_choices import (
    choices_for_character,
    migrate_legacy_sheet,
    validate_creation_choices,
)
from backend.games.dnd5e.characters.entity import character_from_dict, character_to_dict
from backend.games.dnd5e.characters.origin_feats import (
    normalize_origin_feat_id,
    origin_feat_passive_lines,
)
from backend.games.dnd5e.dm.agents.nodes import resource_keeper_node
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_rest,
    combat_blocks_rest,
    narration_sets_mage_armor,
    overlay_live_resources,
    parse_pc_hp_from_narration,
    rest_granted,
    rest_refused,
)
from backend.games.dnd5e.dm.spell_autocomplete import extract_cast_query
from backend.games.registry import preserve_live_resources


def _wizard2() -> dict:
    """QA Wizard 2 5375bf52: Human Sage, Magic Initiate (Wizard), no auto Shield."""
    return {
        "id": "5375bf52",
        "name": "QA Wizard 2",
        "species": "human",
        "class_name": "wizard",
        "level": 1,
        "background": "sage",
        "origin_feat": "Magic Initiate (Wizard)",
        "versatile_origin_feat": "Alert",
        "ability_scores": {"str": 8, "dex": 14, "con": 15, "int": 16, "wis": 12, "cha": 10},
        "ability_scores_set": True,
        "hp": 8,
        "max_hp": 8,
        "ac": 12,
        "armor": "none",
        "hit_dice_max": 1,
        "hit_dice_spent": 0,
        "cantrips": ["Fire Bolt", "Mage Hand", "Prestidigitation"],
        "prepared_spells": ["Detect Magic", "Mage Armor", "Magic Missile", "Sleep"],
        "spellbook": [
            "Detect Magic",
            "Mage Armor",
            "Magic Missile",
            "Sleep",
            "Burning Hands",
            "Charm Person",
        ],
        "spell_slots": {"1": 2},
        "feature_choices": {"human_skill": "perception"},
        "classes": [{"class_name": "wizard", "level": 1}],
    }


def test_finnish_combat_rest_is_refused_and_not_applied():
    refused = "Lepo saisi odottaa. Olette kesken taistelun."
    assert rest_refused(refused)
    assert not rest_granted(refused, kind="short")
    data = _wizard2()
    data["hp"] = 3
    data["spell_slots"] = {"1": 1}
    entity, logs = apply_pending_rest(
        data,
        {"kind": "short", "dice_to_spend": 1},
        refused,
        combat_active=True,
    )
    assert entity == {}
    assert any("combat" in line.lower() or "not applied" in line.lower() for line in logs)


def test_resource_keeper_combat_rest_does_not_heal_or_recover_slots():
    data = _wizard2()
    data["hp"] = 3
    data["spell_slots"] = {"1": 1}
    state = {
        "shortcut_result": {
            "task": "short_rest",
            "pending_rest": {"kind": "short", "dice_to_spend": 1},
        },
        "response": "Lepo saisi odottaa. Olette kesken taistelun.",
        "character": data,
        "user_message": "**Short rest**\n\nThe player tries to take a short rest.",
        "combat_state": {"status": "active"},
        "session_id": "e1822ee3",
    }
    result = resource_keeper_node(state)
    updates = result.get("character_updates") or {}
    assert updates.get("hp") != 8
    assert "hit_dice_spent" not in updates
    slots = updates.get("spell_slots") or {}
    assert slots.get("1", 1) == 1
    assert any("not applied" in line.lower() for line in result.get("resource_log") or [])


def test_combat_blocks_rest_uses_active_encounter():
    assert combat_blocks_rest(combat_state={"status": "active"}) is True
    assert combat_blocks_rest(combat_state={"status": "ended"}) is False
    assert combat_blocks_rest(combat_state={}) is False


def test_finnish_hp_4_of_8_is_parsed_and_overlaid():
    text = "Rotan purema osuu. HP 4/8. Jatka varovasti."
    hp = parse_pc_hp_from_narration(text, name="QA Wizard 2", max_hp=8, current_hp=8)
    assert hp == 4
    updates = overlay_live_resources(_wizard2(), text)
    assert updates.get("hp") == 4


def test_bare_cast_spell_message_does_not_apply_mage_armor():
    from backend.games.dnd5e.actions import run_shortcut

    result = run_shortcut("cast_spell", **_wizard2())
    assert result.get("entity_updates") == {}
    mention = (
        "No spell named. Which prepared spell: Mage Armor, Magic Missile, Detect Magic, Sleep?"
    )
    assert narration_sets_mage_armor(mention) is False
    updates = overlay_live_resources(_wizard2(), mention)
    assert not (updates.get("feature_choices") or {}).get("_mage_armor_active")
    assert updates.get("ac") in (None, 12)


def test_cast_mage_armor_narration_still_sets_flag():
    text = "You cast Mage Armor. The ward shimmers; AC is 15."
    assert narration_sets_mage_armor(text) is True
    updates = overlay_live_resources(_wizard2(), text)
    assert updates.get("feature_choices", {}).get("_mage_armor_active") is True
    assert updates.get("ac") == 15


def test_character_page_ac_uses_mage_armor_flag():
    data = _wizard2()
    data["feature_choices"] = {"_mage_armor_active": True, "human_skill": "perception"}
    merged = preserve_live_resources(data, character_to_dict(rebuild_character(character_from_dict(data))))
    assert merged["feature_choices"].get("_mage_armor_active") is True
    details = compute_ac_details(character_from_dict(merged))
    assert int(details["computed"]) == 15


def test_preserve_does_not_infer_mage_armor_from_stored_ac():
    stored = _wizard2()
    stored["ac"] = 15
    rebuilt = character_to_dict(rebuild_character(character_from_dict(stored)))
    merged = preserve_live_resources(stored, rebuilt)
    assert not merged["feature_choices"].get("_mage_armor_active")
    details = compute_ac_details(character_from_dict(merged))
    assert int(details["computed"]) == 12


def test_magic_initiate_wizard_label_does_not_become_cleric():
    assert normalize_origin_feat_id("Magic Initiate (Wizard)") == "magic_initiate_wizard"
    assert normalize_origin_feat_id("Magic Initiate (Cleric)") == "magic_initiate_cleric"
    char = character_from_dict(_wizard2())
    lines = origin_feat_passive_lines(char)
    feats = {row["feat"] for row in lines}
    assert "Magic Initiate (Wizard)" in feats
    assert "Magic Initiate (Cleric)" not in feats


def test_sage_wizard_creation_asks_for_mi_picks_once():
    char = rebuild_character(character_from_dict(_wizard2()))
    migrate_legacy_sheet(char)
    missing = " | ".join(validate_creation_choices(char)).lower()
    assert "magic initiate" in missing
    choices = choices_for_character(char)
    mi_ids = [c["id"] for c in choices if str(c.get("id") or "").startswith("magic_initiate")]
    assert mi_ids.count("magic_initiate_cantrips") == 1
    assert mi_ids.count("magic_initiate_level1") == 1
    level1 = next(c for c in choices if c["id"] == "magic_initiate_level1")
    options = [str(s).lower() for s in (level1.get("spell_options") or [])]
    assert "shield" in options
    assert "magic missile" in options
    assert str(char.feature_choices.get("magic_initiate_level1") or "") == ""


def test_existing_mi_pick_is_kept_not_replaced_with_shield():
    data = _wizard2()
    data["feature_choices"] = {
        "human_skill": "perception",
        "magic_initiate_level1": "Magic Missile",
        "magic_initiate_cantrips": ["Minor Illusion", "Acid Splash"],
        "magic_initiate_ability": "int",
    }
    char = character_from_dict(data)
    migrate_legacy_sheet(char)
    assert str(char.feature_choices.get("magic_initiate_level1")).lower() == "magic missile"


def test_free_cast_summary_is_not_parsed_as_no_slot_spent_spell():
    summary = (
        "**Cast spell**\n\n"
        "Magic Missile: Magic Initiate free cast (no slot spent)."
    )
    assert extract_cast_query(summary) is None
    assert extract_cast_query("/cast_spell") is None
    assert extract_cast_query("Yes, cast Shield (Magic Initiate free)")
