"""Initiative combat: start encounters, auto-resolve enemy turns."""

from __future__ import annotations

import random
import re
import uuid
from typing import Any

from backend.dm.audit import character_audit_slice, record_audit
from backend.dm.encounters import (
    Combatant,
    CombatState,
    EncounterSpec,
    clear_combat_state,
    load_adventure_encounters,
    load_combat_state,
    load_completed_encounter_ids,
    mark_encounter_completed,
    save_combat_state,
)
from backend.dm.story_director import load_story_progress
from backend.games.dnd5e.characters.entity import (
    Dnd5eCharacter,
    character_from_dict,
    character_to_dict,
)
from backend.games.dnd5e.dm.monster_resolver import lookup_monster
from backend.play_tools import roll_dice


def _initiative_mod(char: Dnd5eCharacter) -> int:
    return char.initiative_modifier()


def _dex_mod(char: Dnd5eCharacter) -> int:
    return (char.ability_scores.get("dex", 10) - 10) // 2


def _con_mod(char: Dnd5eCharacter) -> int:
    return (char.ability_scores.get("con", 10) - 10) // 2


def _proficiency_bonus(char: Dnd5eCharacter) -> int:
    return 2 + (max(1, char.level) - 1) // 4


def _con_save_proficient(char: Dnd5eCharacter) -> bool:
    profs = [p.lower() for p in (char.save_proficiencies or [])]
    if "con" in profs:
        return True
    cls = (char.class_name or "").lower()
    return cls in ("barbarian", "fighter", "sorcerer")


def check_concentration_save(char: Dnd5eCharacter, damage: int) -> tuple[bool, str]:
    """Roll a CON save to maintain concentration after taking damage.

    DC = max(10, damage // 2) per PHB 2024.
    Returns (maintained, summary_line).
    """
    if not char.concentration:
        return True, ""
    dc = max(10, damage // 2)
    mod = _con_mod(char)
    if _con_save_proficient(char):
        mod += _proficiency_bonus(char)
    result = roll_dice("1d20", caller="combat_manager.concentration")
    roll_val = int(result["rolls"][0])
    total = roll_val + mod
    maintained = roll_val == 20 or (roll_val != 1 and total >= dc)
    spell = char.concentration
    if maintained:
        summary = (
            f"**Concentration save** (d20 {roll_val} + {mod} = {total} vs DC {dc}): "
            f"**MAINTAINED** {spell}"
        )
    else:
        summary = (
            f"**Concentration save** (d20 {roll_val} + {mod} = {total} vs DC {dc}): "
            f"**LOST** {spell}"
        )
    record_audit(
        {
            "event": "concentration",
            "source": "combat_manager",
            "detail": {
                "spell": spell,
                "dc": dc,
                "roll": roll_val,
                "total": total,
                "maintained": maintained,
                "damage": damage,
                "inferred": False,
            },
        }
    )
    return maintained, summary


def _roll_initiative(mod: int = 0, *, caller: str = "combat_manager.initiative") -> int:
    result = roll_dice("1d20", caller=caller)
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
                    multiattack_count=max(1, stats.multiattack_count),
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
    player.initiative = _roll_initiative(_initiative_mod(char))
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
    record_audit(
        {
            "event": "combat_start",
            "source": "combat_manager",
            "detail": {
                "encounter_id": encounter.id,
                "encounter_name": encounter.name,
                "initiative": [
                    {"id": c.id, "name": c.name, "initiative": c.initiative} for c in combatants
                ],
                "inferred": False,
            },
        },
        session_id=session_id,
    )
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
    atk = roll_dice("1d20", caller="combat_manager.attack")
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
        dmg = roll_dice(dmg_expr, caller="combat_manager.damage")
        damage = int(dmg.get("total", 0))
        damage_summary = f" for **{damage}** damage"
    result = {
        "attacker": enemy.name,
        "roll": roll,
        "total": total,
        "hit": hit,
        "crit": crit,
        "damage": damage,
        "summary": (
            f"**{enemy.name}** attacks "
            f"(d20 {roll} + {enemy.attack_bonus} = {total} "
            f"vs AC {target_ac}): " + ("**HIT**" if hit else "miss") + damage_summary
        ),
    }
    record_audit(
        {
            "event": "combat_attack",
            "source": "combat_manager",
            "detail": {
                "attacker": enemy.name,
                "roll": roll,
                "attack_bonus": enemy.attack_bonus,
                "total": total,
                "target_ac": target_ac,
                "hit": hit,
                "crit": crit,
                "damage": damage,
                "inferred": False,
            },
        }
    )
    return result


def apply_damage_to_player(char_dict: dict, damage: int) -> dict:
    before = character_audit_slice(char_dict)
    char = character_from_dict(char_dict)
    char.hp = max(0, char.hp - damage)
    after_dict = character_to_dict(char)
    record_audit(
        {
            "event": "hp_change",
            "source": "combat_manager",
            "before": before,
            "after": character_audit_slice(after_dict),
            "detail": {"damage": damage, "inferred": False},
        }
    )
    return after_dict


def resolve_enemy_turn(state: CombatState, char_dict: dict) -> tuple[CombatState, dict, list[str]]:
    """Resolve one enemy's turn. Returns (updated state, updated char dict, event lines)."""
    events: list[str] = []
    actor = current_combatant(state)
    if not actor or actor.kind != "enemy" or actor.hp <= 0:
        return state, char_dict, events

    player = _combatant_by_id(state, "player")
    target_ac = player.ac if player else character_from_dict(char_dict).ac
    num_attacks = max(1, actor.multiattack_count)
    if num_attacks > 1:
        events.append(f"**{actor.name}** uses Multiattack ({num_attacks} attacks)")
    for _ in range(num_attacks):
        result = resolve_enemy_attack(actor, target_ac)
        events.append(result["summary"])
        if result["hit"] and result["damage"] > 0:
            char_dict = apply_damage_to_player(char_dict, result["damage"])
            if player:
                player.hp = character_from_dict(char_dict).hp
            char = character_from_dict(char_dict)
            maintained, conc_summary = check_concentration_save(char, result["damage"])
            if conc_summary:
                events.append(conc_summary)
                if not maintained:
                    char_dict["concentration"] = ""

    state = advance_turn(state)
    if _all_enemies_defeated(state):
        state.status = "ended"
    return state, char_dict, events


def run_enemy_turns_until_player(
    session_id: str,
    char_dict: dict,
    *,
    resolve_enemies: bool = True,
) -> tuple[CombatState | None, dict, list[str]]:
    """Auto-resolve consecutive enemy turns until player's turn or combat ends."""
    state = load_combat_state(session_id)
    if not state:
        return None, char_dict, []
    if not resolve_enemies:
        return state, char_dict, []

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
                _finish_combat(session_id, state)
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
            _finish_combat(session_id, state)
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
        multi = f", multiattack ×{c.multiattack_count}" if c.multiattack_count > 1 else ""
        atk = (
            f", attack +{c.attack_bonus} {c.damage}{multi}"
            if c.kind == "enemy" and c.attack_bonus
            else ""
        )
        lines.append(f"- {c.name} [{c.kind}]: {status}{init}{atk}")
    if actor and actor.kind == "player":
        lines.append(
            "It is the player's turn. Resolve their action, then enemies act in initiative order."
        )
    elif actor and actor.kind == "enemy":
        lines.append("Enemy turns are resolved mechanically before narration when possible.")
    return "\n".join(lines)


def _finish_combat(session_id: str, state: CombatState) -> None:
    mark_encounter_completed(session_id, state.encounter_id)
    clear_combat_state(session_id)
    save_combat_state(session_id, state)


def pick_encounter_to_start(
    adventure_id: str,
    *,
    session_id: str = "",
    active_beat: str = "",
    active_beat_notes: str = "",
    user_message: str = "",
    recent_dm_text: str = "",
) -> EncounterSpec | None:
    """Choose a planned encounter when the story beat or scene calls for combat."""
    encounters = load_adventure_encounters(adventure_id)
    if not encounters:
        return None

    completed: set[str] = load_completed_encounter_ids(session_id) if session_id else set()
    pending = [enc for enc in encounters if enc.id not in completed]
    if not pending:
        return None

    best: EncounterSpec | None = None
    best_beat_score = 0
    best_total = 0
    for enc in pending:
        beat_score, reactive_score = _score_encounter_match(
            enc,
            active_beat=active_beat,
            active_beat_notes=active_beat_notes,
            user_message=user_message,
            recent_dm_text=recent_dm_text,
        )
        total = beat_score + reactive_score
        if beat_score > best_beat_score or (beat_score == best_beat_score and total > best_total):
            best_beat_score = beat_score
            best_total = total
            best = enc
        elif beat_score == best_beat_score and total > best_total:
            best_total = total
            best = enc

    if best is None:
        return None
    reactive = best_total - best_beat_score
    # Explicit trigger alignment in story beat (exact, title, or notes context).
    if best_beat_score >= 75:
        return best
    # Reactive ambush: combat cues in the scene and player/scene action.
    if best_total >= 55 and reactive >= 15:
        return best
    return None


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def _text_aligns(a: str, b: str) -> bool:
    a_norm = _normalize_text(a)
    b_norm = _normalize_text(b)
    if not a_norm or not b_norm:
        return False
    if a_norm in b_norm or b_norm in a_norm:
        return True
    words_a = {w for w in a_norm.split() if len(w) > 3}
    words_b = {w for w in b_norm.split() if len(w) > 3}
    overlap = words_a & words_b
    # Require two shared meaningful words; single-word overlap (e.g. "harbor") is too loose.
    return len(overlap) >= 2


_COMBAT_HINTS = (
    "encounter:",
    "boss fight",
    "combat",
    "ambush",
    "assault",
    "battle",
)


def _has_active_combat_hint(text: str) -> bool:
    lowered = _normalize_text(text)
    if "encounter:" in lowered:
        return True
    patterns = (
        r"\bcombat\b",
        r"\bfight\b",
        r"\bboss\b",
        r"\bambush\b",
        r"\bbattle\b",
        r"\bassault\b",
        r"\brepel\b",
        r"\bsurge\b",
        r"\battack\b",
        r"\braid\b",
    )
    return any(re.search(p, lowered) for p in patterns)


def _trigger_in_context(trigger: str, ctx: str) -> bool:
    if not trigger or not ctx:
        return False
    pattern = r"\b" + re.escape(trigger) + r"\b"
    return bool(re.search(pattern, ctx))


def _message_has_combat_intent(msg: str) -> bool:
    lowered = msg.lower()
    triggers = (
        "attack",
        "fight",
        "combat",
        "initiative",
        "charge",
        "strike",
        "shoot",
        "swing",
        "kill",
        "/initiative",
        "/attack",
    )
    return any(t in lowered for t in triggers)


_COMBAT_PLAYER_TASKS = frozenset(
    {"attack_roll", "initiative", "death_save", "cast_spell", "saving_throw"}
)


def player_took_combat_action(
    user_message: str,
    shortcut_result: dict | None = None,
) -> bool:
    """True when the player message should advance the combat turn."""
    task = (shortcut_result or {}).get("task", "")
    if task in _COMBAT_PLAYER_TASKS:
        return True
    return _message_has_combat_intent(user_message)


def _score_encounter_match(
    enc: EncounterSpec,
    *,
    active_beat: str,
    active_beat_notes: str,
    user_message: str,
    recent_dm_text: str,
) -> tuple[int, int]:
    beat_score = 0
    reactive_score = 0
    beat_title = _normalize_text(active_beat)
    beat_notes = _normalize_text(active_beat_notes)
    beat_ctx = _normalize_text(f"{active_beat} {active_beat_notes}")
    trigger = _normalize_text(enc.trigger_beat)
    enc_name = _normalize_text(enc.name)
    enc_desc = _normalize_text(enc.description)

    if beat_title and trigger:
        if trigger == beat_title:
            beat_score += 100
        elif _trigger_in_context(trigger, beat_title):
            beat_score += 85
        elif _trigger_in_context(trigger, beat_ctx):
            beat_score += 75

    if beat_title and (_text_aligns(enc_name, beat_title) or _text_aligns(enc_desc, beat_title)):
        beat_score += 70

    if beat_notes and "encounter:" in beat_notes:
        for enemy in enc.enemies:
            monster = _normalize_text(enemy.monster_name)
            if monster and monster in beat_notes:
                beat_score += 80

    if trigger and _trigger_in_context(trigger, beat_ctx):
        beat_score += 20
    if enc_name and enc_name in beat_ctx:
        beat_score += 15

    for enemy in enc.enemies:
        monster = _normalize_text(enemy.monster_name)
        label = _normalize_text(enemy.label)
        if monster and monster in beat_ctx and _has_active_combat_hint(beat_ctx):
            beat_score += 25
        if label and label in beat_ctx and _has_active_combat_hint(beat_ctx):
            beat_score += 15

    if enc_name and enc_name in _normalize_text(user_message):
        reactive_score += 40
    for enemy in enc.enemies:
        if enemy.monster_name.lower() in user_message.lower():
            reactive_score += 35

    if _message_has_combat_intent(user_message):
        reactive_score += 15

    if recent_dm_text and _has_active_combat_hint(recent_dm_text):
        for enemy in enc.enemies:
            if enemy.monster_name.lower() in recent_dm_text.lower():
                reactive_score += 25

    return beat_score, reactive_score


def _recent_dm_text(messages: list | None) -> str:
    for msg in reversed(messages or []):
        if msg.get("role") == "assistant":
            return str(msg.get("content") or "")
    return ""


def try_start_planned_encounter(
    session_id: str,
    adventure_id: str,
    char_dict: dict,
    *,
    user_message: str = "",
    messages: list | None = None,
) -> CombatState | None:
    """Start a planned encounter when the story beat or scene calls for combat."""
    existing = load_combat_state(session_id)
    if existing:
        return existing

    active_beat = ""
    active_beat_notes = ""
    progress = load_story_progress(adventure_id)
    if progress:
        active = next((c for c in progress.checkpoints if c.status == "active"), None)
        if active:
            active_beat = active.title
            active_beat_notes = active.dm_notes or ""

    enc = pick_encounter_to_start(
        adventure_id,
        session_id=session_id,
        active_beat=active_beat,
        active_beat_notes=active_beat_notes,
        user_message=user_message,
        recent_dm_text=_recent_dm_text(messages),
    )
    if not enc:
        return None
    # Do not start combat on a purely social/exploration message unless the scene is hot.
    recent = _recent_dm_text(messages)
    if not player_took_combat_action(user_message) and not _has_active_combat_hint(recent):
        return None
    return start_encounter(session_id, enc, char_dict)
