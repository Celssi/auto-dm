"""QA of Paladin playthrough #24: shown replies, rest, HD, LoH, DCs, NPC rename."""

import pytest

from backend.games.dnd5e.characters.entity import character_from_dict, remaining_int
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_rest,
    merge_active_effects,
    overlay_live_resources,
    parse_conditions_from_narration,
    parse_hit_dice_remaining,
    parse_lay_on_hands_spend,
    rest_granted,
    rest_refused,
)
from backend.games.dnd5e.dm.agents.nodes import continuity_guard_node
from backend.storage import persist_shown_reply, persist_user_message


@pytest.fixture(autouse=True)
def disable_gcs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTO_DM_BUCKET", "")


def _paladin(*, hp: int = 12, loh: int = 0, hit_dice_spent: int = 0, conditions=None) -> dict:
    return {
        "id": "paladin-qa",
        "name": "QA Paladin",
        "species": "human",
        "class_name": "paladin",
        "level": 1,
        "hp": hp,
        "max_hp": 12,
        "ac": 18,
        "hit_die": 10,
        "hit_dice_max": 1,
        "hit_dice_spent": hit_dice_spent,
        "lay_on_hands_remaining": loh,
        "conditions": list(conditions or []),
        "concentration": "Bless",
        "spell_slots": {"1": 1},
        "classes": [{"class_name": "paladin", "level": 1}],
        "inventory": ["chalk", "button"],
        "currency": {"gp": 23, "cp": 7},
    }


def test_remaining_int_keeps_zero():
    assert remaining_int(0) == 0
    assert remaining_int(None) == -1
    assert remaining_int("") == -1
    assert remaining_int(5) == 5


def test_lay_on_hands_zero_survives_rebuild():
    char = character_from_dict(_paladin(loh=0))
    assert char.lay_on_hands_remaining == 0


def test_continuity_guard_never_rewrites():
    out = continuity_guard_node(
        {
            "narrative": "You heal the goblin with Lay on Hands. It surrenders.",
            "response": "You heal the goblin with Lay on Hands. It surrenders.",
            "narrative_context": {"canon_summary": "x", "recent_scenes": "y"},
        }
    )
    assert out == {}


def test_hit_dice_unused_recap_does_not_spend():
    text = "You rest for an hour. Hit Dice 0/1 unused. Lay on Hands pool unchanged."
    assert parse_hit_dice_remaining(text, hit_dice_max=1) == 1
    overlay = overlay_live_resources(_paladin(hit_dice_spent=0), text)
    assert overlay.get("hit_dice_spent") in (None, 0)


def test_short_rest_not_refused_by_hit_dice_not_applied():
    from backend.games.dnd5e.dm.mechanics_delta import render_mechanics_block

    dm = (
        "You take a short rest. An hour later you stand. Hit dice not applied.\n"
        + render_mechanics_block({"rest": {"kind": "short", "hit_dice_spent": 0}})
    )
    assert not rest_refused(dm)
    assert rest_granted(dm, kind="short")
    updates, logs = apply_pending_rest(
        _paladin(hp=8),
        {"kind": "short", "dice_to_spend": 0},
        dm,
        user_message="**Short rest**",
    )
    assert updates or logs
    assert not any("refused" in line.lower() for line in logs)


def test_ogre_not_frightened_does_not_clear_pc_frightened():
    current = ["Frightened", "Poisoned"]
    out = parse_conditions_from_narration(
        "The ogre is not Frightened of you. A poisoned dart sits on the table.",
        current,
    )
    assert "Frightened" in out
    assert "Poisoned" in out


def test_frightened_save_dc_stays_fixed():
    current = [{"name": "Frightened", "source": "goblin", "save_dc": 11}]
    merged = merge_active_effects(
        current,
        ["Frightened"],
        "The goblin shrieks. Wisdom saving throw DC 13. You are still Frightened.",
    )
    assert merged[0]["save_dc"] == 11


def test_lay_on_hands_spend_from_narration():
    from backend.games.dnd5e.dm.mechanics_delta import render_mechanics_block

    assert parse_lay_on_hands_spend("Lay on Hands heals 5 points.", 5) == 0
    overlay = overlay_live_resources(
        _paladin(loh=5),
        "You use Lay on Hands to heal 5 HP.\n"
        + render_mechanics_block({"resources": {"lay_on_hands": 5}, "hp_changes": [{"amount": 5, "source": "Lay on Hands"}]}),
    )
    assert overlay.get("lay_on_hands_remaining") == 0


def test_concentration_not_cleared_by_sheet_recap():
    overlay = overlay_live_resources(_paladin(), "Concentration field reads none.")
    assert overlay.get("concentration") in (None, "Bless")


def test_persist_shown_reply_does_not_replace(isolated_saves):
    from backend import storage

    storage.save_character("hero", {"name": "Hero", "game_id": "dnd5e"})
    adv = storage.save_adventure("adv1", {"name": "Quest", "character_id": "hero"})
    sid = storage.create_session(character_id="hero", adventure_id=adv, name="QA")
    persist_user_message(sid, "I use Lay on Hands.")
    persist_shown_reply(sid, "I use Lay on Hands.", "You spend 5 points. The goblin surrenders.")
    persist_shown_reply(sid, "I use Lay on Hands.", "Lay on Hands is not needed. No surrender.")
    messages = storage.get_session(sid)["messages"]
    assert messages[-1]["content"] == "You spend 5 points. The goblin surrenders."
    assert "not needed" not in messages[-1]["content"]


def test_npc_rename_merges_grek_to_snag(isolated_saves):
    from backend import journal_storage
    from backend.dm.journal_keeper import apply_detected_renames

    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": []})
    journal_storage.save_campaign_npc("camp", None, {"name": "Grek", "body": "A goblin at the door."})
    apply_detected_renames("camp", "Grek grins. His true name is Snag.")
    npcs = journal_storage.list_campaign_npcs("camp")
    assert [row["name"] for row in npcs] == ["Snag"]
    entry = journal_storage.get_campaign_npc("camp", npcs[0]["id"])
    assert "Grek" in (entry.get("aliases") or [])
