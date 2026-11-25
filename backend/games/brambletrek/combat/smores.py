"""Smores ally in Frozen Forest combat (CDE printed pp. 110–111).

The book gives daily abilities, turn order, and a tactic table, but no starting
Health and no defeat rule. Smores therefore has no base HP bar and cannot be
knocked out; intercepted attacks are soaked by Shield and temporary health,
with any overflow hitting the player (core combat still turns on the Gnawborn).
"""

from __future__ import annotations

from typing import Any, Callable

SMORES_ID = "smores"
DAILY_SHIELD = "shield"
DAILY_SWEET_TREAT = "sweet_treat"


def lookup_smores_tactic(card: str) -> dict[str, Any] | None:
    from backend.games.brambletrek.modules.loader import lookup_module_scene_row

    row = lookup_module_scene_row("first_frost", "smores_tactics", card)
    if not isinstance(row, dict):
        return None
    body = str(row.get("body") or "").strip()
    label = str(row.get("label") or "").strip()
    text = f"{label}. {body}".strip(". ") if body and body not in label else label or body
    return {**row, "label": text, "card": card}


def smores_present(state: dict[str, Any]) -> bool:
    ally = state.get("ally")
    return isinstance(ally, dict) and ally.get("id") == SMORES_ID


def smores_ally(state: dict[str, Any]) -> dict[str, Any]:
    ally = state.get("ally")
    if not isinstance(ally, dict):
        ally = {"id": SMORES_ID, "label": "Smores"}
        state["ally"] = ally
    return ally


def new_smores_ally(*, hand: list[str], daily_used: str = "") -> dict[str, Any]:
    return {
        "id": SMORES_ID,
        "label": "Smores",
        "temp_hp": 0,
        "temp_hp_turns": 0,
        "hand": list(hand),
        "needs_new_round": False,
        "intercept_next": False,
        "daily_used": str(daily_used or ""),
        "shield_armed": False,
        "extra_turns": 0,
    }


def tick_smores_durations(state: dict[str, Any]) -> list[str]:
    """Tick temp HP and Guard after an opponent turn (a 'turn' of duration)."""
    lines: list[str] = []
    if not smores_present(state):
        return lines
    ally = smores_ally(state)
    turns = int(ally.get("temp_hp_turns") or 0)
    if turns > 0:
        if ally.get("temp_hp_fresh"):
            ally["temp_hp_fresh"] = False
        else:
            ally["temp_hp_turns"] = turns - 1
            if ally["temp_hp_turns"] <= 0:
                ally["temp_hp_turns"] = 0
                leftover = int(ally.get("temp_hp") or 0)
                ally["temp_hp"] = 0
                if leftover:
                    lines.append("Smores' temporary health fades.")
    buffs = state.setdefault("buffs", {})
    reflect_turns = int(buffs.get("smores_reflect_turns") or 0)
    if reflect_turns > 0:
        if buffs.get("smores_reflect_fresh"):
            buffs["smores_reflect_fresh"] = False
        else:
            buffs["smores_reflect_turns"] = reflect_turns - 1
            if buffs["smores_reflect_turns"] <= 0:
                buffs.pop("smores_reflect_turns", None)
                buffs.pop("smores_reflect", None)
                lines.append("Smores drops his Guard stance.")
    return lines


def use_daily_ability(
    state: dict[str, Any],
    ability: str,
    *,
    target: str = "player",
) -> list[str]:
    from backend.games.brambletrek.combat.effects import change_morale, heal_player

    if not smores_present(state):
        raise ValueError("Smores is not in this fight")
    ally = smores_ally(state)
    used = str(ally.get("daily_used") or "")
    if used:
        raise ValueError("Smores has already used a daily ability today")
    ability = ability.strip().lower()
    lines: list[str] = []
    if ability == DAILY_SHIELD:
        ally["daily_used"] = DAILY_SHIELD
        ally["shield_armed"] = True
        if target == "smores":
            ally["intercept_next"] = True
            lines.append(
                "Smores readies Shield: the next attack directed at him is reduced by 3 "
                "(CDE p. 110)."
            )
        else:
            lines.append(
                "Smores readies Shield: the next attack directed at you is reduced by 3 "
                "(CDE p. 110)."
            )
    elif ability == DAILY_SWEET_TREAT:
        ally["daily_used"] = DAILY_SWEET_TREAT
        lines.append("Smores offers a Sweet Treat (CDE p. 110).")
        heal_player(state, 2, lines, source="Smores")
        change_morale(state, 1, lines)
    else:
        raise ValueError("Smores can use Shield or Sweet Treat")
    state["smores_daily_used"] = ally["daily_used"]
    return lines


def set_intercept(state: dict[str, Any], enabled: bool) -> list[str]:
    if not smores_present(state):
        raise ValueError("Smores is not in this fight")
    ally = smores_ally(state)
    ally["intercept_next"] = bool(enabled)
    if enabled:
        return ["Smores will take the next attack directed at the group."]
    return ["Smores will not intercept the next attack."]


def apply_incoming_to_smores(
    state: dict[str, Any],
    damage: int,
    lines: list[str],
    *,
    source: str,
) -> int:
    """Soak intercepted damage with Shield and temp HP; return leftover for the player."""
    from backend.games.brambletrek.combat.effects import damage_opponent

    ally = smores_ally(state)
    remaining = int(damage)
    if ally.get("shield_armed"):
        cut = min(3, remaining)
        remaining -= cut
        ally["shield_armed"] = False
        lines.append(f"Smores' Shield absorbs {cut} damage.")
    buffs = state.setdefault("buffs", {})
    reflect = int(buffs.get("smores_reflect") or 0)
    if reflect > 0 and int(buffs.get("smores_reflect_turns") or 0) > 0:
        lines.append(f"Smores' Guard reflects {reflect} damage back at {source}!")
        damage_opponent(state, reflect, lines, actor_label="Smores", attack=False)
    temp = int(ally.get("temp_hp") or 0)
    if remaining > 0 and temp > 0:
        soaked = min(temp, remaining)
        ally["temp_hp"] = temp - soaked
        remaining -= soaked
        lines.append(f"Smores' temporary health absorbs {soaked} damage.")
    ally["intercept_next"] = False
    if remaining > 0:
        lines.append(
            f"Smores cannot absorb the remaining {remaining} "
            "(the book gives him no Health value); it hits you."
        )
    elif damage > 0:
        lines.append("Smores shrugs off the blow.")
    return remaining


Draw = Callable[[int], list[str]]
