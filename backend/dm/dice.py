"""Dice helpers for D&D solo play."""

from __future__ import annotations

from typing import Any, Literal

from backend.play_tools import format_dice_result, roll_dice

Advantage = Literal["normal", "advantage", "disadvantage"]


def _build_d20_summary(rolls: list[int], modifier: int, advantage: Advantage) -> str:
    if advantage == "advantage":
        chosen = max(rolls)
        total = chosen + modifier
        return (
            f"d20 advantage: rolled {rolls[0]} and {rolls[1]}, kept {chosen}"
            + (f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else "")
            + f" = **{total}**"
        )
    if advantage == "disadvantage":
        chosen = min(rolls)
        total = chosen + modifier
        return (
            f"d20 disadvantage: rolled {rolls[0]} and {rolls[1]}, kept {chosen}"
            + (f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else "")
            + f" = **{total}**"
        )
    total = rolls[0] + modifier
    mod_str = f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else ""
    return f"**1d20{mod_str}**: [{rolls[0]}]{mod_str} = **{total}**"


def _build_d20_result(rolls: list[int], modifier: int, advantage: Advantage) -> dict[str, Any]:
    if advantage in ("advantage", "disadvantage"):
        pick = max if advantage == "advantage" else min
        chosen = pick(rolls)
    else:
        chosen = rolls[0]
    total = chosen + modifier
    return {
        "ok": True,
        "rolls": rolls,
        "chosen": chosen,
        "modifier": modifier,
        "total": total,
        "summary": _build_d20_summary(rolls, modifier, advantage),
        "advantage": advantage,
    }


def roll_advantage_d20(
    modifier: int = 0,
    *,
    advantage: Advantage = "normal",
    pre_rolled: list[int] | None = None,
) -> dict[str, Any]:
    if pre_rolled is not None:
        return _build_d20_result(pre_rolled, modifier, advantage)
    if advantage in ("advantage", "disadvantage"):
        a = roll_dice("1d20")
        b = roll_dice("1d20")
        rolls = [int(a["rolls"][0]), int(b["rolls"][0])]
        return _build_d20_result(rolls, modifier, advantage)
    result = roll_dice(f"1d20{modifier:+d}" if modifier else "1d20")
    return {
        "ok": True,
        "rolls": list(result.get("rolls", [])),
        "chosen": int(result.get("total", 0)) - modifier,
        "modifier": modifier,
        "total": int(result.get("total", 0)),
        "summary": format_dice_result(result),
        "advantage": advantage,
    }


def roll_death_saves(pre_rolled: int | None = None) -> dict[str, Any]:
    if pre_rolled is not None:
        roll = pre_rolled
    else:
        result = roll_dice("1d20")
        roll = int(result["rolls"][0])
    if roll == 1:
        outcome = "two failures"
    elif roll == 20:
        outcome = "regain 1 HP and wake"
    elif roll >= 10:
        outcome = "success"
    else:
        outcome = "failure"
    return {
        "ok": True,
        "roll": roll,
        "outcome": outcome,
        "summary": f"Death save: **{roll}** — {outcome}",
    }
