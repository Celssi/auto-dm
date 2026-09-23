"""Apply structured tactic effects from curated YAML metadata."""

from __future__ import annotations

import re
from typing import Any


def _infer_buffs_from_label(label: str) -> dict[str, Any]:
    """Fallback when tactic rows lack structured buff fields."""
    lbl = label.lower()
    meta: dict[str, Any] = {}
    if any(p in lbl for p in ("skip your", "you miss", "you skip", "lose your next turn", "stuns the player")):
        meta["skip_turn"] = True
    if "attacks miss" in lbl or "attack misses" in lbl:
        turns = 3 if "3 turn" in lbl else 2 if "2 turn" in lbl else 1
        meta["player_attacks_miss_turns"] = turns
    if ("halves" in lbl or "half" in lbl) and "damage" in lbl and "your" not in lbl:
        turns = 3 if "three" in lbl or "3" in lbl else 2 if "two" in lbl or "2" in lbl else 1
        meta["halve_incoming_turns"] = turns
    if "evade" in lbl and "next attack" in lbl:
        meta["evade_next"] = 1
    m = re.search(r"reduces? (?:your|the player'?s?) (?:attack|damage) by (\d+)", lbl)
    if m:
        meta["reduce_player_damage"] = int(m.group(1))
        meta["reduce_player_damage_turns"] = 2 if "2 turn" in lbl else 3 if "3 turn" in lbl else 1
    m = re.search(r"\+(\d+) damage", lbl)
    if m and "next" in lbl:
        meta["damage_bonus"] = int(m.group(1))
        meta["damage_bonus_turns"] = 2 if "2 turn" in lbl else 1
    return meta


def _apply_buff_metadata(tactic: dict[str, Any], buffs: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, buff_key in (
        ("halve_incoming_turns", "halve_incoming_turns"),
        ("reduce_player_damage_turns", "reduce_player_damage_turns"),
        ("reduce_opponent_damage_turns", "reduce_opponent_damage_turns"),
        ("damage_bonus_turns", "damage_bonus_turns"),
        ("skip_opponent_turns", "skip_opponent_turns"),
        ("player_attacks_miss_turns", "player_attacks_miss_turns"),
        ("opponent_armor_turns", "opponent_armor_turns"),
        ("heal_per_turn_turns", "heal_per_turn_turns"),
    ):
        if tactic.get(key):
            buffs[buff_key] = int(buffs.get(buff_key) or 0) + int(tactic[key])
            lines.append(f"Buff: {buff_key.replace('_', ' ')} for {tactic[key]} turn(s).")
    for key in (
        "reduce_player_damage",
        "reduce_opponent_damage",
        "damage_bonus",
        "opponent_armor",
        "heal_per_turn",
    ):
        if tactic.get(key) is not None:
            buffs[key] = int(tactic[key])
    if tactic.get("evade_next"):
        buffs["evade_next"] = int(buffs.get("evade_next") or 0) + int(tactic["evade_next"])
    if tactic.get("reflect_next"):
        buffs["reflect_next"] = int(buffs.get("reflect_next") or 0) + int(tactic["reflect_next"])
    if tactic.get("opponent_evades_next"):
        buffs["opponent_evades_next"] = int(buffs.get("opponent_evades_next") or 0) + int(
            tactic["opponent_evades_next"]
        )
    if tactic.get("opponent_halve_next"):
        buffs["opponent_halve_next"] = int(buffs.get("opponent_halve_next") or 0) + int(
            tactic["opponent_halve_next"]
        )
    if tactic.get("skip_turn"):
        buffs["skip_player"] = int(buffs.get("skip_player") or 0) + 1
    if tactic.get("critical"):
        buffs["critical"] = True
    inferred = _infer_buffs_from_label(str(tactic.get("label") or tactic.get("effect") or ""))
    for k, v in inferred.items():
        if k in tactic or (k in buffs and buffs[k]):
            continue
        if k == "skip_turn":
            buffs["skip_player"] = int(buffs.get("skip_player") or 0) + 1
        elif isinstance(v, int):
            buffs[k] = int(buffs.get(k) or 0) + v
        elif v is True:
            buffs[k] = True
    return lines


def tick_turn_buffs(buffs: dict[str, Any]) -> None:
    """Decay turn-based buff counters at end of a full round."""
    for key in (
        "halve_incoming_turns",
        "reduce_player_damage_turns",
        "reduce_opponent_damage_turns",
        "damage_bonus_turns",
        "skip_opponent_turns",
        "opponent_armor_turns",
        "heal_per_turn_turns",
    ):
        if int(buffs.get(key) or 0) > 0:
            buffs[key] = int(buffs[key]) - 1
            if buffs[key] <= 0:
                buffs.pop(key, None)
                if key == "reduce_player_damage_turns":
                    buffs.pop("reduce_player_damage", None)
                if key == "reduce_opponent_damage_turns":
                    buffs.pop("reduce_opponent_damage", None)
                if key == "damage_bonus_turns":
                    buffs.pop("damage_bonus", None)
                if key == "opponent_armor_turns":
                    buffs.pop("opponent_armor", None)
                if key == "heal_per_turn_turns":
                    buffs.pop("heal_per_turn", None)


def _apply_player_damage_to_opponent(
    state: dict[str, Any],
    damage: int,
    lines: list[str],
    *,
    actor_label: str = "You",
) -> int:
    buffs = state.setdefault("buffs", {})
    opponent = state.setdefault("opponent", {})
    if int(buffs.get("player_attacks_miss_turns") or 0) > 0:
        buffs["player_attacks_miss_turns"] = int(buffs["player_attacks_miss_turns"]) - 1
        lines.append("Your attack misses!")
        state["buffs"] = buffs
        return 0
    if int(buffs.get("opponent_evades_next") or 0) > 0:
        buffs["opponent_evades_next"] = int(buffs["opponent_evades_next"]) - 1
        lines.append("The opponent evades your attack!")
        state["buffs"] = buffs
        return 0
    bonus = int(buffs.get("damage_bonus") or 0)
    penalty = int(buffs.get("reduce_player_damage") or 0)
    if buffs.get("critical") and damage > 0:
        damage *= 2
        buffs["critical"] = False
        lines.append("Critical hit — double damage!")
    damage = max(0, damage + bonus - penalty)
    opp_reduction = int(buffs.get("reduce_opponent_damage") or 0)
    damage = max(0, damage - opp_reduction)
    if int(buffs.get("opponent_halve_next") or 0) > 0 and damage > 0:
        damage = (damage + 1) // 2
        buffs["opponent_halve_next"] = int(buffs["opponent_halve_next"]) - 1
        lines.append("Opponent's guard halves your damage.")
    armor = int(buffs.get("opponent_armor") or 0)
    if armor > 0:
        damage = max(0, damage - armor)
    if damage > 0:
        opponent["hp"] = max(0, int(opponent.get("hp") or 0) - damage)
        state["opponent"] = opponent
        prog = state.setdefault("phase_progress", {})
        prog["damage_dealt"] = int(prog.get("damage_dealt") or 0) + damage
        lines.append(f"{actor_label} deal {damage} damage to {opponent.get('label', 'opponent')}.")
    state["buffs"] = buffs
    return damage


def apply_tactic_effects(
    state: dict[str, Any],
    tactic: dict[str, Any] | None,
    *,
    actor: str,
) -> list[str]:
    """Mutate combat state from tactic row. Returns log lines."""
    if not tactic:
        return [f"{actor}: no tactic resolved."]
    lines: list[str] = [
        f"**{actor.title() if actor == 'item' else actor}** — {tactic.get('label', tactic.get('effect', '?'))}"
    ]
    buffs = state.setdefault("buffs", {})
    opponent = state.get("opponent") or {}
    player = state.get("player") or {}

    damage = int(tactic.get("damage") or 0)
    heal = int(tactic.get("heal") or 0)

    if actor == "player":
        _apply_player_damage_to_opponent(state, damage, lines)
        if heal > 0:
            player["hp"] = min(20, int(player.get("hp") or 0) + heal)
            state["player"] = player
            lines.append(f"Healed {heal} health.")
        lines.extend(_apply_buff_metadata(tactic, buffs))
    elif actor == "opponent":
        if int(buffs.get("reflect_next") or 0) > 0 and damage > 0:
            buffs["reflect_next"] = int(buffs["reflect_next"]) - 1
            opponent["hp"] = max(0, int(opponent.get("hp") or 0) - damage)
            state["opponent"] = opponent
            lines.append(f"Reflected {damage} damage back to {opponent.get('label', 'opponent')}!")
            state["buffs"] = buffs
            return lines
        if int(buffs.get("evade_next") or 0) > 0:
            buffs["evade_next"] = int(buffs["evade_next"]) - 1
            lines.append("You evade the attack!")
            state["buffs"] = buffs
            lines.extend(_apply_buff_metadata(tactic, buffs))
            return lines
        if int(buffs.get("skip_opponent_turns") or 0) > 0:
            buffs["skip_opponent_turns"] = int(buffs["skip_opponent_turns"]) - 1
            lines.append("Aerith is stunned and skips this attack.")
            state["buffs"] = buffs
            lines.extend(_apply_buff_metadata(tactic, buffs))
            return lines
        halve_turns = int(buffs.get("halve_incoming_turns") or 0)
        if halve_turns > 0 and damage > 0:
            damage = (damage + 1) // 2
            buffs["halve_incoming_turns"] = halve_turns - 1
            lines.append("Incoming damage halved.")
        if damage > 0:
            player["hp"] = max(0, int(player.get("hp") or 0) - damage)
            state["player"] = player
            lines.append(f"You take {damage} damage.")
        if heal > 0:
            opponent["hp"] = min(int(opponent.get("max_hp") or 20), int(opponent.get("hp") or 0) + heal)
            state["opponent"] = opponent
            lines.append(f"Opponent heals {heal}.")
        lines.extend(_apply_buff_metadata(tactic, buffs))
    elif actor == "eolan":
        if damage > 0:
            _apply_player_damage_to_opponent(state, damage, lines, actor_label="Eolan")
        if int(tactic.get("self_damage") or 0) > 0:
            sd = int(tactic["self_damage"])
            player["hp"] = max(0, int(player.get("hp") or 0) - sd)
            state["player"] = player
            lines.append(f"Daring Feint — you take {sd} damage.")
        if heal > 0:
            player["hp"] = min(20, int(player.get("hp") or 0) + heal)
            state["player"] = player
            lines.append(f"Eolan heals you {heal}.")
        lines.extend(_apply_buff_metadata(tactic, buffs))
    elif actor == "item":
        lines.extend(_apply_buff_metadata(tactic, buffs))
        if damage > 0:
            _apply_player_damage_to_opponent(state, damage, lines, actor_label="Item")
        if heal > 0:
            player["hp"] = min(20, int(player.get("hp") or 0) + heal)
            state["player"] = player
            lines.append(f"Item heals {heal} health.")
    state["buffs"] = buffs
    return lines
