"""Dice rolling utilities."""

from __future__ import annotations

import random
import re
from typing import Any


def roll_dice(notation: str) -> dict[str, Any]:
    """Roll dice from notation like 1d20+5, 2d6, d20."""
    notation = notation.strip().lower().replace(" ", "")
    match = re.match(r"^(\d*)d(\d+)([+-]\d+)?$", notation)
    if not match:
        count = 1
        sides = 20
        modifier = 0
        if notation.isdigit():
            sides = int(notation)
        else:
            return {"ok": False, "summary": f"Invalid dice notation: {notation}"}
    else:
        count = int(match.group(1) or 1)
        sides = int(match.group(2))
        modifier = int(match.group(3) or 0)

    count = max(1, min(100, count))
    sides = max(2, min(1000, sides))
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    mod_str = f" {'+' if modifier >= 0 else ''}{modifier}" if modifier else ""
    summary = f"**{notation}**: {rolls}{mod_str} = **{total}**"
    return {"ok": True, "rolls": rolls, "modifier": modifier, "total": total, "summary": summary}


def format_dice_result(result: dict[str, Any]) -> str:
    return str(result.get("summary", ""))
