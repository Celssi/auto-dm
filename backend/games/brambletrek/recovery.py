"""Resting and the Recovery Tables (Core Rulebook pp. 15-16)."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.effects import MAX_STAT, half_up
from backend.games.brambletrek.dm.curated import lookup_recovery
from backend.games.brambletrek.rag_config import GAME_ID
from backend.play_tools import draw_cards, reset_deck

REST_SUPPLY_COST = 4  # p. 15: spend 4 Supplies when resting...
REST_HEALTH_GAIN = 2  # ...to restore 2 Health.
RECOVERY_STATS = ("health", "morale", "supplies")


def _draw_one(char_id: str) -> str:
    result = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        reset_deck(GAME_ID, char_id)
        result = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Recovery draw failed")
    return str(result["cards"][0])


def recover_resource(char: BrambletrekCharacter, stat: str, *, char_id: str) -> dict[str, Any]:
    """Lose a day recovering: stat returns to half of max (rounded up); draw a prompt (p. 16)."""
    card = _draw_one(char_id)
    row = lookup_recovery(stat, card) or {}
    before = int(getattr(char, stat))
    after = max(before, half_up(MAX_STAT))
    setattr(char, stat, after)
    char.clamp_stats()
    return {
        "stat": stat,
        "card": card,
        "label": str(row.get("label") or ""),
        "before": before,
        "after": int(getattr(char, stat)),
    }


def resolve_zero_resources(char: BrambletrekCharacter, *, char_id: str) -> list[dict[str, Any]]:
    """Any resource at 0 triggers its Recovery Table (p. 16)."""
    return [
        recover_resource(char, stat, char_id=char_id)
        for stat in RECOVERY_STATS
        if int(getattr(char, stat)) <= 0
    ]


def stats_at_zero(char: BrambletrekCharacter) -> list[str]:
    return [stat for stat in RECOVERY_STATS if int(getattr(char, stat)) <= 0]


def merge_pending_recovery_stats(
    pending: list[str] | None,
    char: BrambletrekCharacter,
    *,
    forced: list[str] | None = None,
) -> list[str]:
    """Resources still at 0 after today's events (recovery is checked at day end).

    A mid-day dip to 0 that a later event heals does not force a recovery day.
    `forced` marks (e.g. Supplies Recovery when you cannot afford rest) stay even above 0.
    Stale values in `pending` are ignored once the resource is above 0 again.
    """
    marked = set(stats_at_zero(char))
    for stat in forced or []:
        if stat in RECOVERY_STATS:
            marked.add(str(stat))
    return [stat for stat in RECOVERY_STATS if stat in marked]


def apply_pending_recoveries(
    char: BrambletrekCharacter, stats: list[str], *, char_id: str
) -> list[dict[str, Any]]:
    """Restore each marked stat to half of max on the recovery day (one table draw per stat)."""
    recoveries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for stat in RECOVERY_STATS:
        if stat not in stats or stat in seen:
            continue
        seen.add(stat)
        recoveries.append(recover_resource(char, stat, char_id=char_id))
    return recoveries


def rest_at_day_end(
    char: BrambletrekCharacter, *, char_id: str, resolve_zeros: bool = True
) -> dict[str, Any]:
    """End-of-day rest (p. 15): pay 4 Supplies for +2 Health, else Supplies Recovery now."""
    if int(char.supplies) >= REST_SUPPLY_COST:
        char.supplies = int(char.supplies) - REST_SUPPLY_COST
        before = int(char.health)
        char.health = min(MAX_STAT, before + REST_HEALTH_GAIN)
        recoveries = resolve_zero_resources(char, char_id=char_id) if resolve_zeros else []
        return {
            "rested": True,
            "supplies_spent": REST_SUPPLY_COST,
            "health_gained": int(char.health) - before,
            "recoveries": recoveries,
        }
    if resolve_zeros:
        recoveries = [recover_resource(char, "supplies", char_id=char_id)]
        recoveries.extend(resolve_zero_resources(char, char_id=char_id))
        return {
            "rested": False,
            "supplies_spent": 0,
            "health_gained": 0,
            "recoveries": recoveries,
        }
    return {
        "rested": False,
        "supplies_spent": 0,
        "health_gained": 0,
        "recoveries": [],
        "needs_supplies_recovery": True,
    }


def format_recovery(rec: dict[str, Any]) -> str:
    stat = str(rec.get("stat") or "").title()
    label = rec.get("label") or "recover"
    return (
        f"{stat} Recovery — {rec.get('card')}: {label}. You lose a day; "
        f"{stat} {rec.get('before')}→{rec.get('after')}."
    )
