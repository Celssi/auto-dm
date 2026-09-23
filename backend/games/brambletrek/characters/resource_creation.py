"""Character resource creation: six-card draws, values, low-roll bonus."""

from __future__ import annotations

from typing import Any, Literal

from backend.games.brambletrek.characters.entity import (
    STAT_MAX,
    STAT_MIN,
    BrambletrekCharacter,
    legacy_stat_deltas,
)
from backend.games.brambletrek.dm.curated import parse_playing_card
from backend.play_tools import draw_cards, format_card_result

StatKey = Literal["health", "morale", "supplies"]
STAT_KEYS: tuple[StatKey, ...] = ("health", "morale", "supplies")

RESOURCE_DRAFT_KEY = "resource_draft"


def card_resource_value(card: str) -> int:
    parsed = parse_playing_card(card)
    if not parsed:
        return 0
    return int(parsed["numeric_value"])


def pair_sum(cards: list[str]) -> int:
    return sum(card_resource_value(c) for c in cards)


def needs_low_roll_bonus(cards: list[str]) -> bool:
    """True when a stat has exactly two cards totaling 6 or less."""
    return len(cards) == 2 and pair_sum(cards) <= 6


def stat_total(cards: list[str]) -> int:
    return max(STAT_MIN, min(STAT_MAX, pair_sum(cards)))


def default_card_assignment(six_cards: list[str]) -> dict[str, list[str]]:
    if len(six_cards) != 6:
        raise ValueError("Expected six resource cards")
    return {
        "health": [six_cards[0], six_cards[1]],
        "morale": [six_cards[2], six_cards[3]],
        "supplies": [six_cards[4], six_cards[5]],
    }


def compute_base_stats(cards_by_stat: dict[str, list[str]]) -> dict[str, int]:
    return {key: stat_total(list(cards_by_stat.get(key) or [])) for key in STAT_KEYS}


def finals_from_base(
    base: dict[str, int],
    legacy_id: str,
) -> dict[str, int]:
    oh, om, os = legacy_stat_deltas(legacy_id)
    deltas = {"health": oh, "morale": om, "supplies": os}
    return {
        key: max(STAT_MIN, min(STAT_MAX, int(base.get(key, 0)) + deltas[key])) for key in STAT_KEYS
    }


def resource_draft_payload(
    draft: dict[str, Any],
    *,
    legacy_id: str = "",
) -> dict[str, Any]:
    cards_by_stat = draft.get("cards_by_stat") or {}
    base = compute_base_stats(cards_by_stat)
    pending_bonus = list(draft.get("pending_bonus") or [])
    stats: list[dict[str, Any]] = []
    for key in STAT_KEYS:
        cards = list(cards_by_stat.get(key) or [])
        stats.append(
            {
                "stat": key,
                "cards": cards,
                "pair_sum": pair_sum(cards) if cards else 0,
                "base": base[key],
                "needs_bonus": key in pending_bonus,
                "card_values": [card_resource_value(c) for c in cards],
            }
        )
    payload: dict[str, Any] = {
        "cards_by_stat": cards_by_stat,
        "pending_bonus": pending_bonus,
        "base_stats": base,
        "stats": stats,
        "remaining": draft.get("remaining"),
    }
    if legacy_id:
        payload["final_stats"] = finals_from_base(base, legacy_id)
    return payload


def _new_draft(cards_by_stat: dict[str, list[str]], *, remaining: int) -> dict[str, Any]:
    pending = [key for key in STAT_KEYS if needs_low_roll_bonus(cards_by_stat.get(key, []))]
    return {
        "cards_by_stat": cards_by_stat,
        "pending_bonus": pending,
        "remaining": remaining,
    }


def draw_character_resources(
    *,
    game_id: str,
    char_id: str | None,
    legacy_id: str = "",
) -> dict[str, Any]:
    result = draw_cards(count=6, game_id=game_id, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or result.get("summary") or "Deck draw failed")
    cards = list(result["cards"])
    draft = _new_draft(default_card_assignment(cards), remaining=int(result.get("remaining", 0)))
    return {
        "draft": draft,
        "draw_summary": format_card_result(result),
        **resource_draft_payload(draft, legacy_id=legacy_id),
    }


def draw_resource_bonus(
    draft: dict[str, Any],
    stat: str,
    *,
    game_id: str,
    char_id: str | None,
    legacy_id: str = "",
) -> dict[str, Any]:
    if stat not in STAT_KEYS:
        raise ValueError(f"Invalid stat: {stat}")
    pending = list(draft.get("pending_bonus") or [])
    if stat not in pending:
        raise ValueError(f"No low-roll bonus draw pending for {stat}")
    result = draw_cards(count=1, game_id=game_id, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or result.get("summary") or "Deck draw failed")
    card = result["cards"][0]
    cards_by_stat = {k: list(v) for k, v in (draft.get("cards_by_stat") or {}).items()}
    cards_by_stat.setdefault(stat, []).append(card)
    pending = [s for s in pending if s != stat]
    # Re-check: if still only 2 cards and still low, allow another bonus? Rule says one extra per stat.
    updated = {
        "cards_by_stat": cards_by_stat,
        "pending_bonus": pending,
        "remaining": int(result.get("remaining", 0)),
    }
    return {
        "draft": updated,
        "draw_summary": format_card_result(result),
        "bonus_card": card,
        **resource_draft_payload(updated, legacy_id=legacy_id),
    }


def apply_resource_draft(char: BrambletrekCharacter, draft: dict[str, Any]) -> BrambletrekCharacter:
    cards_by_stat = draft.get("cards_by_stat") or {}
    if not all(len(cards_by_stat.get(k) or []) >= 2 for k in STAT_KEYS):
        raise ValueError("Assign at least two resource cards per stat before applying")
    base = compute_base_stats(cards_by_stat)
    char.resource_cards = {k: list(cards_by_stat.get(k) or []) for k in STAT_KEYS}
    char.resource_base_health = base["health"]
    char.resource_base_morale = base["morale"]
    char.resource_base_supplies = base["supplies"]
    finals = finals_from_base(base, char.legacy)
    char.health = finals["health"]
    char.morale = finals["morale"]
    char.supplies = finals["supplies"]
    char.clamp_stats()
    return char


def roll_legacy() -> dict[str, Any]:
    from backend.games.brambletrek.dm.curated import legacy_by_roll, legacy_id_by_roll
    from backend.play_tools import format_dice_result, roll_dice

    roll = roll_dice("d6")
    if not roll.get("ok"):
        raise ValueError(roll.get("error") or "d6 roll failed")
    total = int(roll["total"])
    legacy_id = legacy_id_by_roll(total)
    return {
        "roll": roll,
        "roll_formatted": format_dice_result(roll),
        "legacy_id": legacy_id,
        "legacy_label": legacy_by_roll(total),
    }
