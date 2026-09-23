"""Tests for Brambletrek resource creation math."""

from __future__ import annotations

from backend.games.brambletrek.characters.resource_creation import (
    card_resource_value,
    compute_base_stats,
    default_card_assignment,
    finals_from_base,
    needs_low_roll_bonus,
    pair_sum,
    stat_total,
)


def test_card_values_ace_and_face() -> None:
    assert card_resource_value("Ace of hearts") == 11
    assert card_resource_value("King of spades") == 10
    assert card_resource_value("5 of clubs") == 5


def test_default_assignment_and_totals() -> None:
    cards = [
        "2 of hearts",
        "3 of diamonds",
        "4 of clubs",
        "5 of spades",
        "6 of hearts",
        "7 of diamonds",
    ]
    by_stat = default_card_assignment(cards)
    assert by_stat["health"] == cards[0:2]
    assert by_stat["morale"] == cards[2:4]
    assert by_stat["supplies"] == cards[4:6]
    assert pair_sum(by_stat["health"]) == 5
    assert needs_low_roll_bonus(by_stat["health"]) is True
    assert needs_low_roll_bonus(by_stat["morale"]) is False


def test_stat_total_clamps() -> None:
    assert stat_total(["Ace of hearts", "King of spades"]) == 20


def test_finals_from_base_with_legacy() -> None:
    base = {"health": 12, "morale": 10, "supplies": 8}
    finals = finals_from_base(base, "seer")
    assert finals["health"] >= 0
    assert all(v <= 20 for v in finals.values())


def test_compute_base_stats() -> None:
    by_stat = {
        "health": ["Ace of hearts", "2 of clubs"],
        "morale": ["5 of hearts", "5 of diamonds"],
        "supplies": ["10 of spades", "Jack of clubs"],
    }
    base = compute_base_stats(by_stat)
    assert base["health"] == 13
    assert base["morale"] == 10
    assert base["supplies"] == 20
