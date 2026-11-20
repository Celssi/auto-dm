"""QA of #23: fall damage, rest grant, conditions, errors, lonelog."""

from backend.dm.audit import format_audit_summary
from backend.dm.errors import friendly_dm_error
from backend.dm.lonelog import strip_markdown
from backend.games.dnd5e.dm.resource_keeper import (
    apply_pending_rest,
    overlay_live_resources,
    parse_conditions_from_narration,
    parse_pc_hp_from_narration,
    rest_granted,
    rest_refused,
)


def _sage(*, hp: int = 8, conditions=None) -> dict:
    return {
        "id": "51e929c7",
        "name": "QA Sage 4",
        "species": "human",
        "class_name": "wizard",
        "level": 1,
        "hp": hp,
        "max_hp": 8,
        "ac": 15,
        "hit_die": 6,
        "hit_dice_max": 1,
        "hit_dice_spent": 0,
        "conditions": list(conditions or []),
        "spell_slots": {"1": 1},
        "classes": [{"class_name": "wizard", "level": 1}],
    }


def test_friendly_error_hides_anthropic_credit_payload():
    raw = "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_abc'}"
    msg = friendly_dm_error(raw)
    assert "credits exhausted" in msg.lower()
    assert "req_abc" not in msg
    assert "400" not in msg


def test_second_fall_uses_this_turn_dice_not_prior_damage():
    text = (
        "Earlier you fell for 3. Falling: 1d6 = 3. HP 8 -> 5/8, Prone. "
        "This landing: Falling: 1d6 = 4. HP 8 -> 1/8, Prone."
    )
    assert parse_pc_hp_from_narration(text, name="QA Sage 4", max_hp=8, current_hp=8) == 4
    overlay = overlay_live_resources(_sage(hp=8), text)
    assert overlay.get("hp") == 4
    logs = " ".join(overlay.get("_logs") or [])
    assert "Took 4 damage" in logs
    assert "7" not in logs


def test_fall_still_applies_single_roll():
    text = "Falling: 1d6 = 3. HP 8 -> 5/8, Prone"
    assert parse_pc_hp_from_narration(text, name="QA Sage 4", max_hp=8, current_hp=8) == 5
    overlay = overlay_live_resources(_sage(hp=8), text)
    assert overlay.get("hp") == 5
    assert "Prone" in (overlay.get("conditions") or [])
    assert any("Took 3 damage" in line for line in overlay.get("_logs") or [])


def test_named_conditions_need_pc_targeting():
    text = (
        "The ogre is Frightened of the wizard. A poisoned dart sits on the table. "
        "You keep your feet."
    )
    assert parse_conditions_from_narration(text, []) == []
    overlay = overlay_live_resources(_sage(hp=8), text)
    assert not overlay.get("conditions")


def test_prone_from_fall_still_applies():
    assert "Prone" in parse_conditions_from_narration("Falling: 1d6 = 3. HP 8 -> 5/8, Prone", [])


def test_short_rest_grants_when_prone_ends():
    dm = "You sit for an hour. Prone ended. You catch your breath and stand."
    assert not rest_refused(dm)
    assert rest_granted(dm, kind="short")
    updates, logs = apply_pending_rest(
        _sage(hp=4, conditions=["Prone"]),
        {"kind": "short", "dice_to_spend": 1},
        dm,
        user_message="**Short rest**",
    )
    assert updates
    assert not any("refused" in line.lower() or "did not grant" in line.lower() for line in logs)


def test_keep_moving_does_not_refuse_a_granted_rest():
    dm = "You take a short rest. An hour later you keep moving down the road."
    assert not rest_refused(dm)
    assert rest_granted(dm, kind="short")


def test_explicit_rest_refusal_still_blocks():
    refused = "Short rest: not possible. Mott is less than a minute away. Automated result not applied."
    assert rest_refused(refused)
    assert not rest_granted(refused, kind="short")


def test_character_patch_audit_mentions_damage():
    summary = format_audit_summary(
        {
            "event": "character_patch",
            "diff": {"hp": {"before": 8, "after": 4}, "conditions": {"before": [], "after": ["Prone"]}},
            "detail": {"damage": 4, "notes": ["Took 4 damage (HP 8 -> 4/8)."]},
        }
    )
    assert "Took 4 damage" in summary
    assert "8" in summary
    assert "4" in summary


def test_lonelog_strips_markdown():
    assert strip_markdown("**Prone ended.** You rest.") == "Prone ended. You rest."
