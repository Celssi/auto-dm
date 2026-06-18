"""Initiative combat: start encounters, auto-resolve enemy turns."""

from __future__ import annotations

import random
import uuid
from typing import Any

from backend.characters.entity import Dnd5eCharacter, character_from_dict, character_to_dict
from backend.dm.encounters import (
    CombatState,
    Combatant,
    EncounterSpec,
    clear_combat_state,
    load_adventure_encounters,
    load_combat_state,
    save_combat_state,
)
from backend.dm.monster_resolver import lookup_monster
from backend.play_tools import roll_dice


def _dex_mod(char: Dnd5eCharacter) -> int:
    return (char.ability_scores.get("dex", 10) - 10) // 2


def _roll_initiative(mod: int = 0) -> int:
    result = roll_dice("1d20")
    return int(result["rolls"][0]) + mod


def _primary_attack(stats) -> tuple[int, str]:
    if stats.attacks:
        atk = stats.attacks[0]
        return int(atk.to_hit), str(atk.damage or "1d6")
    return 4, "1d6+2"


def spawn_enemy_combatants(spec_enemies: list, encounter_id: str) -> list[Combatant]:
    combatants: list[Combatant] = []
    for group in spec_enemies:
        stats = lookup_monster(group.monster_name)
        to_hit, damage = _primary_attack(stats)
        label = (group.label or group.monster_name).strip()
        for i in range(group.count):
            suffix = f" {i + 1}" if group.count > 1 else ""
            combatants.append(
                Combatant(
                    id=f"{encounter_id}-enemy-{uuid.uuid4().hex[:6]}",
                    name=f"{label}{suffix}".strip(),
                    kind="enemy",
                    monster_name=group.monster_name,
                    hp=stats.hp,
                    max_hp=stats.hp,
                    ac=stats.ac,
                    attack_bonus=to_hit,
                    damage=damage,
                )
            )
    return combatants


def build_player_combatant(char: Dnd5eCharacter) -> Combatant:
    return Combatant(
        id="player",
        name=char.name or "Hero",
        kind="player",
        initiative=0,
        hp=char.hp,
        max_hp=char.max_hp,
        ac=char.ac,
    )


def roll_initiative_for_state(state: CombatState) -> CombatState:
    for c in state.combatants:
        if c.kind == "player":
            char = None
            for pc in state.combatants:
                if pc.kind == "player":
                    c.initiative = _roll_initiative(0)
            continue
        c.initiative = _roll_initiative(random.randint(-1, 2))
    state.order = sorted(
        [c.id for c in state.combatants if c.hp > 0],
        key=lambda cid: next(c.initiative for c in state.combatants if c.id == cid),
        reverse=True,
    )
    state.turn_index = 0
    state.round = 1
    return state


def start_encounter(
    session_id: str,
    encounter: EncounterSpec,
    char_dict: dict,
) -> CombatState:
    char = character_from_dict(char_dict)
    player = build_player_combatant(char)
    player.initiative = _roll_initiative(_dex_mod(char))
    enemies = spawn_enemy_combatants(encounter.enemies, encounter.id)
    for e in enemies:
        e.initiative = _roll_initiative(random.randint(0, 2))
    combatants = [player] + enemies
    state = CombatState(
        encounter_id=encounter.id,
        encounter_name=encounter.name,
        combatants=combatants,
    )
    state.order = sorted(
        [c.id for c in combatants],
        key=lambda cid: next(c.initiative for c in combatants if c.id == cid),
        reverse=True,
    )
    state.turn_index = 0
    state.round = 1
    save_combat_state(session_id, state)
    return state


def current_combatant(state: CombatState) -> Combatant | None:
    if not state.order or state.status != "active":
        return None
    cid = state.order[state.turn_index % len(state.order)]
    return next((c for c in state.combatants if c.id == cid), None)


def _combatant_by_id(state: CombatState, cid: str) -> Combatant | None:
    return next((c for c in state.combatants if c.id == cid), None)


def advance_turn(state: CombatState) -> CombatState:
    if not state.order:
        return state
    state.turn_index += 1
    if state.turn_index >= len(state.order):
        state.turn_index = 0
        state.round += 1
    return state


def _living_enemies(state: CombatState) -> list[Combatant]:
    return [c for c in state.combatants if c.kind == "enemy" and c.hp > 0]


def _all_enemies_defeated(state: CombatState) -> bool:
    return not _living_enemies(state)


def resolve_enemy_attack(enemy: Combatant, target_ac: int) -> dict[str, Any]:
    atk = roll_dice("1d20")
    roll = int(atk["rolls"][0])
    total = roll + enemy.attack_bonus
    hit = roll == 20 or (roll != 1 and total >= target_ac)
    crit = roll == 20
    damage = 0
    damage_summary = ""
    if hit:
        dmg_expr = enemy.damage or "1d6"
        if crit:
            parts = dmg_expr.split("+")
            base = parts[0].strip()
            if "d" in base:
                count, rest = base.split("d", 1)
                dmg_expr = f"{int(count) * 2}d{rest}"
        dmg = roll_dice(dmg_expr)
        damage = int(dmg.get("total", 0))
        damage_summary = f" for **{damage}** damage"
    return {
        "attacker": enemy.name,
        "roll": roll,
        "total": total,
        "hit": hit,
        "crit": crit,
        "damage": damage,
        "summary": (
            f"**{enemy.name}** attacks (d20 {roll} + {enemy.attack_bonus} = {total} vs AC {target_ac}): "
            + ("**HIT**" if hit else "miss")
            + damage_summary
        ),
    }


def apply_damage_to_player(char_dict: dict, damage: int) -> dict:
    char = character_from_dict(char_dict)
    char.hp = max(0, char.hp - damage)
    return character_to_dict(char)


def resolve_enemy_turn(state: CombatState, char_dict: dict) -> tuple[CombatState, dict, list[str]]:
    """Resolve one enemy's turn. Returns (updated state, updated char dict, event lines)."""
    events: list[str] = []
    actor = current_combatant(state)
    if not actor or actor.kind != "enemy" or actor.hp <= 0:
        return state, char_dict, events

    player = _combatant_by_id(state, "player")
    target_ac = player.ac if player else character_from_dict(char_dict).ac
    result = resolve_enemy_attack(actor, target_ac)
    events.append(result["summary"])
    if result["hit"] and result["damage"] > 0:
        char_dict = apply_damage_to_player(char_dict, result["damage"])
        player = _combatant_by_id(state, "player")
        if player:
            player.hp = character_from_dict(char_dict).hp

    state = advance_turn(state)
    if _all_enemies_defeated(state):
        state.status = "ended"
    return state, char_dict, events


def run_enemy_turns_until_player(
    session_id: str,
    char_dict: dict,
) -> tuple[CombatState | None, dict, list[str]]:
    """Auto-resolve consecutive enemy turns until player's turn or combat ends."""
    state = load_combat_state(session_id)
    if not state:
        return None, char_dict, []

    all_events: list[str] = []
    safety = 0
    while safety < 20:
        safety += 1
        actor = current_combatant(state)
        if not actor:
            break
        if state.status != "active":
            break
        if actor.kind == "player":
            break
        if actor.kind == "enemy":
            state, char_dict, events = resolve_enemy_turn(state, char_dict)
            all_events.extend(events)
            if state.status == "ended":
                clear_combat_state(session_id)
                save_combat_state(session_id, state)
                break
            save_combat_state(session_id, state)
            continue
        break

    if state and state.status == "active":
        save_combat_state(session_id, state)
    return state, char_dict, all_events


def finish_player_turn(
    session_id: str, char_dict: dict
) -> tuple[CombatState | None, dict, list[str]]:
    """Advance past player turn and run enemy turns until back to player or combat ends."""
    state = load_combat_state(session_id)
    if not state or state.status != "active":
        return state, char_dict, []

    actor = current_combatant(state)
    if actor and actor.kind == "player":
        player = _combatant_by_id(state, "player")
        if player:
            player.hp = character_from_dict(char_dict).hp
        state = advance_turn(state)
        if _all_enemies_defeated(state):
            state.status = "ended"
            clear_combat_state(session_id)
            return state, char_dict, ["All enemies defeated. Combat ended."]
        save_combat_state(session_id, state)

    return run_enemy_turns_until_player(session_id, char_dict)


def format_combat_context(state: CombatState | None) -> str:
    if not state:
        return ""
    lines = [
        f"## Active encounter: {state.encounter_name} (round {state.round})",
    ]
    actor = current_combatant(state)
    if actor:
        lines.append(f"Current turn: **{actor.name}** ({actor.kind})")
    lines.append("Combatants:")
    for c in state.combatants:
        status = "down" if c.hp <= 0 else f"HP {c.hp}/{c.max_hp}, AC {c.ac}"
        init = f", init {c.initiative}" if c.initiative else ""
        atk = (
            f", attack +{c.attack_bonus} {c.damage}" if c.kind == "enemy" and c.attack_bonus else ""
        )
        lines.append(f"- {c.name} [{c.kind}]: {status}{init}{atk}")
    if actor and actor.kind == "player":
        lines.append(
            "It is the player's turn. Resolve their action, then enemies act in initiative order."
        )
    elif actor and actor.kind == "enemy":
        lines.append("Enemy turns are resolved mechanically before narration when possible.")
    return "\n".join(lines)


def pick_encounter_to_start(
    adventure_id: str,
    *,
    active_beat: str = "",
    user_message: str = "",
) -> EncounterSpec | None:
    """Choose a planned encounter matching the current beat or combat trigger."""
    encounters = load_adventure_encounters(adventure_id)
    if not encounters:
        return None
    msg = user_message.lower()
    combat_triggers = ("attack", "fight", "combat", "initiative", "charge", "strike", "/initiative")
    if not any(t in msg for t in combat_triggers):
        return None
    if active_beat:
        beat_lower = active_beat.lower()
        for enc in encounters:
            if enc.trigger_beat and enc.trigger_beat.lower() in beat_lower:
                return enc
            if beat_lower in enc.name.lower() or beat_lower in enc.description.lower():
                return enc
    return encounters[0]
