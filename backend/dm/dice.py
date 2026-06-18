"""Dice helpers for D&D solo play."""

from __future__ import annotations

from typing import Any, Literal

from backend.play_tools import format_dice_result, roll_dice

Advantage = Literal["normal", "advantage", "disadvantage"]


def roll_advantage_d20(
    modifier: int = 0,
    *,
    advantage: Advantage = "normal",
) -> dict[str, Any]:
    if advantage == "advantage":
        a = roll_dice("1d20")
        b = roll_dice("1d20")
        rolls = [int(a["rolls"][0]), int(b["rolls"][0])]
        chosen = max(rolls)
        total = chosen + modifier
        summary = (
            f"d20 advantage: rolled {rolls[0]} and {rolls[1]}, kept {chosen}"
            + (f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else "")
            + f" = **{total}**"
        )
        return {
            "ok": True,
            "rolls": rolls,
            "chosen": chosen,
            "modifier": modifier,
            "total": total,
            "summary": summary,
            "advantage": advantage,
        }
    if advantage == "disadvantage":
        a = roll_dice("1d20")
        b = roll_dice("1d20")
        rolls = [int(a["rolls"][0]), int(b["rolls"][0])]
        chosen = min(rolls)
        total = chosen + modifier
        summary = (
            f"d20 disadvantage: rolled {rolls[0]} and {rolls[1]}, kept {chosen}"
            + (f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else "")
            + f" = **{total}**"
        )
        return {
            "ok": True,
            "rolls": rolls,
            "chosen": chosen,
            "modifier": modifier,
            "total": total,
            "summary": summary,
            "advantage": advantage,
        }
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


def roll_death_saves() -> dict[str, Any]:
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
