"""Dice-only turn classification."""

from backend.dm.turn_kind import is_dice_only_turn


def test_precomputed_dice_shortcut_is_dice_only():
    state = {
        "precomputed_shortcut": {"task": "attack_roll"},
        "shortcut_result": {"task": "attack_roll"},
        "user_message": "Attack roll Strength 14 vs AC",
    }
    assert is_dice_only_turn(state) is True


def test_slash_command_dice_shortcut_is_dice_only():
    state = {
        "shortcut_result": {"task": "ability_check"},
        "user_message": "/ability_check",
    }
    assert is_dice_only_turn(state) is True


def test_freeform_mention_of_attack_roll_is_not_dice_only():
    state = {
        "shortcut_result": {"task": "attack_roll"},
        "user_message": "I make an attack roll against the goblin.",
    }
    assert is_dice_only_turn(state) is False


def test_rest_shortcut_is_not_dice_only():
    state = {
        "precomputed_shortcut": {"task": "short_rest"},
        "shortcut_result": {"task": "short_rest"},
        "user_message": "/short_rest",
    }
    assert is_dice_only_turn(state) is False
