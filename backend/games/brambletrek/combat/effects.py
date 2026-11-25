"""Apply structured tactic effects from curated YAML (Core Rulebook pp. 8, 30-32).

Every tactic row carries its book text in ``label`` plus structured fields; the engine
never infers mechanics from the label. Halving always rounds up (p. 8).

Buff bookkeeping lives in ``state["buffs"]``:

* attack-count buffs are consumed when the matching attack happens
  (``evade_next``, ``damage_bonus_list``, ``reduce_incoming_list``, ``critical`` ...);
* timed buffs live in ``buffs["timed"]`` as ``{key: {"value", "turns", "fresh"}}`` and
  tick at the end of the side's turn listed in ``TIMED_TICK_SIDE``;
* per-turn effects (damage over time, regeneration, companions) are applied by
  :func:`start_player_turn` / :func:`resolve_opponent_turn_effects`.
"""

from __future__ import annotations

from typing import Any, Callable

MAX_STAT = 20

# Which side's turn end ticks a timed buff down.
TIMED_TICK_SIDE = {
    "halve_incoming": "opponent",  # protects you from the opponent's attacks
    "opponent_damage_bonus": "opponent",
    "reduce_player_damage": "player",  # weakens your attacks
    "opponent_armor": "player",
    "damage_bonus": "player",  # legacy module "+N damage for N turns"
}

Draw = Callable[[int], list[str]]


def half_up(value: int) -> int:
    """Halve, rounding up (Core Rulebook p. 8: an Ace = 11 halved is 6)."""
    value = int(value)
    return -((-value) // 2)


def card_value(card: str) -> int:
    from backend.games.brambletrek.dm.curated import parse_playing_card

    parsed = parse_playing_card(card)
    return int(parsed["numeric_value"]) if parsed else 0


# --- state helpers -------------------------------------------------------------------


def player_state(state: dict[str, Any]) -> dict[str, Any]:
    p = state.setdefault("player", {})
    p.setdefault("hp", 0)
    p.setdefault("morale", 0)
    p.setdefault("max_hp", MAX_STAT)
    return p


def opponent_label(state: dict[str, Any]) -> str:
    return str((state.get("opponent") or {}).get("label") or "The opponent")


def _buffs(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault("buffs", {})


def _inc(buffs: dict[str, Any], key: str, by: int = 1) -> None:
    buffs[key] = int(buffs.get(key) or 0) + int(by)


def _consume(buffs: dict[str, Any], key: str) -> bool:
    if int(buffs.get(key) or 0) > 0:
        buffs[key] = int(buffs[key]) - 1
        if buffs[key] <= 0:
            buffs.pop(key, None)
        return True
    return False


def add_timed(state: dict[str, Any], key: str, value: int, turns: int, *, created_by: str) -> None:
    timed = _buffs(state).setdefault("timed", {})
    cur = timed.get(key) or {}
    timed[key] = {
        "value": max(int(cur.get("value") or 0), int(value)),
        "turns": int(cur.get("turns") or 0) + int(turns),
        # A buff created on the side that ticks it must survive that turn's own tick.
        "fresh": TIMED_TICK_SIDE.get(key) == created_by,
    }


def timed_value(state: dict[str, Any], key: str) -> int:
    row = (_buffs(state).get("timed") or {}).get(key)
    if isinstance(row, dict) and int(row.get("turns") or 0) > 0:
        return int(row.get("value") or 0)
    return 0


def tick_timed(state: dict[str, Any], side: str) -> None:
    timed = _buffs(state).get("timed") or {}
    for key in list(timed):
        if TIMED_TICK_SIDE.get(key) != side:
            continue
        row = timed[key]
        if row.get("fresh"):
            row["fresh"] = False
            continue
        row["turns"] = int(row.get("turns") or 0) - 1
        if row["turns"] <= 0:
            timed.pop(key, None)


def tick_turn_buffs(buffs: dict[str, Any]) -> None:
    """Backward-compatible wrapper: tick every timed buff once."""
    state = {"buffs": buffs}
    tick_timed(state, "opponent")
    tick_timed(state, "player")


# --- damage resolution ---------------------------------------------------------------


def damage_opponent(
    state: dict[str, Any],
    damage: int,
    lines: list[str],
    *,
    actor_label: str = "You",
    attack: bool = True,
    use_player_bonuses: bool = True,
) -> int:
    """Deal damage to the opponent (secondary opponent first). ``attack`` applies defences."""
    buffs = _buffs(state)
    opponent = state.setdefault("opponent", {})
    label = opponent_label(state)
    damage = int(damage)
    if attack:
        if _consume(buffs, "player_attacks_miss_turns"):
            lines.append(
                f"{actor_label}r attack misses!"
                if actor_label == "You"
                else f"{actor_label} misses!"
            )
            return 0
        if _consume(buffs, "opponent_evades_next"):
            lines.append(f"{label} evades the attack!")
            return 0
        if use_player_bonuses and damage > 0:
            bonuses = buffs.get("damage_bonus_list") or []
            if bonuses:
                bonus = sum(int(b.get("value") or 0) for b in bonuses)
                damage += bonus
                for b in bonuses:
                    b["attacks"] = int(b.get("attacks") or 1) - 1
                buffs["damage_bonus_list"] = [b for b in bonuses if int(b["attacks"]) > 0]
                lines.append(f"{bonus:+d} damage modifier.")
            damage += timed_value(state, "damage_bonus")
            if buffs.get("critical"):
                damage *= 2
                buffs.pop("critical", None)
                lines.append("Critical — double damage!")
        if damage > 0:
            damage = max(0, damage - timed_value(state, "reduce_player_damage"))
            damage = max(0, damage - timed_value(state, "opponent_armor"))
            if damage > 0 and _consume(buffs, "opponent_halve_next"):
                damage = half_up(damage)
                lines.append(f"{label}'s guard halves the damage.")
    if damage <= 0:
        if attack:
            lines.append(
                f"{actor_label} deal no damage."
                if actor_label == "You"
                else f"{actor_label} deals no damage."
            )
        return 0
    minion = opponent.get("minion") if isinstance(opponent.get("minion"), dict) else None
    remaining = damage
    if minion and int(minion.get("hp") or 0) > 0:
        hit = min(remaining, int(minion["hp"]))
        minion["hp"] = int(minion["hp"]) - hit
        remaining -= hit
        lines.append(
            f"{actor_label} hit the {minion.get('label', 'secondary opponent')} for {hit}."
        )
        if minion["hp"] <= 0:
            opponent.pop("minion", None)
            lines.append(f"The {minion.get('label', 'secondary opponent')} is defeated.")
    if remaining > 0:
        opponent["hp"] = max(0, int(opponent.get("hp") or 0) - remaining)
        verb = "deal" if actor_label == "You" else "deals"
        lines.append(f"{actor_label} {verb} {remaining} damage to {label}.")
        if opponent["hp"] <= 0 and opponent.get("rebirth_armed"):
            opponent.pop("rebirth_armed", None)
            opponent["rebirth_used"] = True
            opponent["hp"] = half_up(int(opponent.get("max_hp") or 0))
            lines.append(f"{label} is reborn with {opponent['hp']} Health!")
    prog = state.setdefault("phase_progress", {})
    prog["damage_dealt"] = int(prog.get("damage_dealt") or 0) + damage
    state["opponent"] = opponent
    return damage


def damage_player(state: dict[str, Any], damage: int, lines: list[str], *, source: str) -> int:
    """Resolve an incoming attack against the Gnawborn, applying defensive buffs."""
    buffs = _buffs(state)
    p = player_state(state)
    damage = int(damage)
    if damage <= 0:
        return 0
    if _consume(buffs, "evade_next"):
        lines.append(f"You avoid {source}'s attack!")
        if buffs.pop("counter_half", None):
            back = half_up(damage)
            lines.append(f"You counter for {back}.")
            damage_opponent(state, back, lines, attack=False)
        return 0
    if _consume(buffs, "reflect_next"):
        lines.append(f"You reflect {damage} damage back!")
        damage_opponent(state, damage, lines, attack=False)
        return 0
    if _consume(buffs, "reflect_half_next"):
        back = half_up(damage)
        lines.append(f"Melodic Mirror reflects {back} damage back!")
        damage_opponent(state, back, lines, attack=False)
        return 0
    reductions = buffs.get("reduce_incoming_list") or []
    if reductions:
        cut = sum(int(r.get("value") or 0) for r in reductions)
        for r in reductions:
            r["attacks"] = int(r.get("attacks") or 1) - 1
        buffs["reduce_incoming_list"] = [r for r in reductions if int(r["attacks"]) > 0]
        damage = max(0, damage - cut)
        lines.append(f"Incoming damage reduced by {cut}.")
    if damage > 0 and (
        timed_value(state, "halve_incoming") or _consume(buffs, "halve_incoming_next")
    ):
        damage = half_up(damage)
        lines.append("Incoming damage halved.")
    if damage <= 0:
        return 0
    p["hp"] = max(0, int(p["hp"]) - damage)
    p["was_hit"] = True
    lines.append(f"You take {damage} damage.")
    return damage


def heal_player(
    state: dict[str, Any], amount: int, lines: list[str], *, source: str = "You"
) -> int:
    p = player_state(state)
    before = int(p["hp"])
    p["hp"] = min(int(p["max_hp"]), before + max(0, int(amount)))
    gained = p["hp"] - before
    if amount > 0:
        lines.append(
            f"{source} restore {gained} Health."
            if source == "You"
            else f"{source} restores {gained} Health."
        )
    return gained


def change_morale(state: dict[str, Any], delta: int, lines: list[str]) -> None:
    p = player_state(state)
    before = int(p["morale"])
    p["morale"] = max(0, min(MAX_STAT, before + int(delta)))
    if p["morale"] != before:
        sign = "+" if delta > 0 else ""
        lines.append(f"Morale {sign}{p['morale'] - before} (now {p['morale']}).")


# --- player-side tactics -------------------------------------------------------------


def _formula_damage(state: dict[str, Any], formula: str) -> int:
    p = player_state(state)
    opp = state.get("opponent") or {}
    if formula == "half_morale":
        return half_up(int(p["morale"]))
    if formula == "half_health":
        return half_up(int(p["hp"]))
    if formula == "opponent_hp_minus_2":
        return max(0, int(opp.get("hp") or 0) - 2)
    if formula == "morale_div_3":
        return int(p["morale"]) // 3
    if formula == "sneak_attack":
        below = max(0, int(p["max_hp"]) - int(p["hp"]))
        return max(0, 10 - below // 3)
    if formula == "shadow_strike":
        return 2 if p.get("was_hit") else 5
    if formula == "half_supplies":
        return half_up(int(p.get("supplies") or 0) + int(p.get("supplies_delta") or 0))
    if formula == "halve_opponent_hp":
        hp = int(opp.get("hp") or 0)
        return hp - half_up(hp)  # health reduced to half, rounded up
    return 0


def _apply_player_side(
    state: dict[str, Any],
    tactic: dict[str, Any],
    lines: list[str],
    *,
    actor_label: str,
    use_player_bonuses: bool,
    draw: Draw | None,
) -> None:
    buffs = _buffs(state)
    p = player_state(state)

    if tactic.get("max_hp_bonus"):
        p["max_hp"] = int(p["max_hp"]) + int(tactic["max_hp_bonus"])
        lines.append(f"Max Health +{tactic['max_hp_bonus']} until the encounter ends.")

    formula = str(tactic.get("damage_formula") or "")
    damage = _formula_damage(state, formula) if formula else int(tactic.get("damage") or 0)
    if formula == "halve_opponent_hp":
        # Not an attack: the opponent's health is halved outright.
        damage_opponent(state, damage, lines, actor_label=actor_label, attack=False)
    elif damage > 0:
        damage_opponent(
            state, damage, lines, actor_label=actor_label, use_player_bonuses=use_player_bonuses
        )

    heal_formula = str(tactic.get("heal_formula") or "")
    if heal_formula == "full":
        heal_player(state, int(p["max_hp"]), lines, source=actor_label)
    elif heal_formula == "half_current":
        heal_player(state, half_up(int(p["hp"])), lines, source=actor_label)
    if int(tactic.get("heal") or 0) > 0 and not tactic.get("heal_per_turn_turns"):
        heal_player(state, int(tactic["heal"]), lines, source=actor_label)
    if tactic.get("heal_from_draw_half") and draw:
        card = draw(1)[0]
        amount = half_up(card_value(card))
        lines.append(f"Drew **{card}** — heal for half its value.")
        heal_player(state, amount, lines, source=actor_label)

    if tactic.get("restore_morale_full"):
        change_morale(state, MAX_STAT, lines)
    elif int(tactic.get("restore_morale") or 0) > 0:
        change_morale(state, int(tactic["restore_morale"]), lines)
    if int(tactic.get("supplies") or 0):
        p["supplies_delta"] = int(p.get("supplies_delta") or 0) + int(tactic["supplies"])
        lines.append(f"Supplies +{int(tactic['supplies'])}.")
    if int(tactic.get("self_damage") or 0) > 0:
        sd = int(tactic["self_damage"])
        p["hp"] = max(0, int(p["hp"]) - sd)
        p["was_hit"] = True
        lines.append(f"You take {sd} damage.")

    # Defences against the opponent's next attack(s).
    if tactic.get("evade_next") or tactic.get("negate_strongest") or tactic.get("evade"):
        _inc(buffs, "evade_next", int(tactic.get("evade_next") or 1))
        if tactic.get("counter_half"):
            buffs["counter_half"] = True
    if tactic.get("reflect_next"):
        _inc(buffs, "reflect_next", int(tactic["reflect_next"]))
    if tactic.get("reflect_half_next"):
        _inc(buffs, "reflect_half_next", int(tactic["reflect_half_next"]))
    reduce_in = int(tactic.get("reduce_incoming") or tactic.get("reduce_opponent_damage") or 0)
    if reduce_in:
        attacks = int(
            tactic.get("reduce_incoming_attacks") or tactic.get("reduce_opponent_damage_turns") or 1
        )
        buffs.setdefault("reduce_incoming_list", []).append(
            {"value": reduce_in, "attacks": attacks}
        )
    if tactic.get("halve_incoming_turns"):
        add_timed(
            state, "halve_incoming", 1, int(tactic["halve_incoming_turns"]), created_by="player"
        )
    if tactic.get("halve_incoming_attacks"):
        _inc(buffs, "halve_incoming_next", int(tactic["halve_incoming_attacks"]))
    if tactic.get("opponent_damage_bonus"):
        # e.g. Grease Trap: the opponent hits harder on its next attack.
        add_timed(
            state,
            "opponent_damage_bonus",
            int(tactic["opponent_damage_bonus"]),
            int(tactic.get("opponent_damage_bonus_turns") or 1),
            created_by="player",
        )

    # Offensive set-ups.
    if tactic.get("damage_bonus"):
        if tactic.get("damage_bonus_turns") and not tactic.get("damage_bonus_attacks"):
            add_timed(
                state,
                "damage_bonus",
                int(tactic["damage_bonus"]),
                int(tactic["damage_bonus_turns"]),
                created_by="ally",
            )
        else:
            buffs.setdefault("damage_bonus_list", []).append(
                {
                    "value": int(tactic["damage_bonus"]),
                    "attacks": int(tactic.get("damage_bonus_attacks") or 1),
                }
            )
    if tactic.get("critical"):
        buffs["critical"] = True
    if tactic.get("skip_opponent_turns"):
        _inc(buffs, "skip_opponent_turns", int(tactic["skip_opponent_turns"]))
        if tactic.get("skip_opponent_effects"):
            buffs["skip_opponent_effects"] = True
    if tactic.get("skip_opponent_after_next"):
        _inc(buffs, "skip_opponent_after_next", int(tactic["skip_opponent_after_next"]))
    if tactic.get("dot_damage"):
        buffs.setdefault("dots", []).append(
            {"damage": int(tactic["dot_damage"]), "turns": int(tactic.get("dot_turns") or 1)}
        )
    if tactic.get("delayed_damage"):
        buffs.setdefault("delayed_damage", []).append(int(tactic["delayed_damage"]))
    if tactic.get("companion_damage"):
        _inc(buffs, "companion_damage", int(tactic["companion_damage"]))
    if tactic.get("heal_per_turn_turns"):
        amount = int(tactic.get("heal_per_turn") or tactic.get("heal") or 0)
        if amount:
            buffs.setdefault("player_regen", []).append(
                {"amount": amount, "turns": int(tactic["heal_per_turn_turns"])}
            )
    if tactic.get("companion_next_encounter"):
        lines.append("A companion will join you for the next encounter (note it in your journal).")


def start_player_turn(state: dict[str, Any]) -> list[str]:
    """Effects that trigger on each of your turns (companions, regen, delayed damage)."""
    lines: list[str] = []
    buffs = _buffs(state)
    regen = buffs.get("player_regen") or []
    for row in regen:
        heal_player(state, int(row["amount"]), lines)
        row["turns"] = int(row["turns"]) - 1
    buffs["player_regen"] = [r for r in regen if int(r["turns"]) > 0]
    delayed = buffs.pop("delayed_damage", None) or []
    for amount in delayed:
        damage_opponent(state, int(amount), lines, attack=False)
    if int(buffs.get("companion_damage") or 0) > 0:
        lines.append("Your companion attacks.")
        damage_opponent(
            state, int(buffs["companion_damage"]), lines, actor_label="Companion", attack=False
        )
    return lines


# --- opponent-side tactics -----------------------------------------------------------


def resolve_opponent_turn_effects(state: dict[str, Any], *, skipped: bool) -> list[str]:
    """Per-opponent-turn effects: damage over time, regeneration, secondary opponent."""
    lines: list[str] = []
    buffs = _buffs(state)
    opponent = state.setdefault("opponent", {})
    if skipped and buffs.pop("skip_opponent_effects", None):
        lines.append("Effects on the opponent's turn are skipped too.")
        return lines
    dots = buffs.get("dots") or []
    total = sum(int(d["damage"]) for d in dots)
    for d in dots:
        d["turns"] = int(d["turns"]) - 1
    buffs["dots"] = [d for d in dots if int(d["turns"]) > 0]
    if total:
        damage_opponent(state, total, lines, actor_label="Lingering effects", attack=False)
    regen = buffs.get("opp_regen") or []
    for row in regen:
        before = int(opponent.get("hp") or 0)
        if before > 0:
            opponent["hp"] = min(int(opponent.get("max_hp") or before), before + int(row["amount"]))
            lines.append(f"{opponent_label(state)} regenerates {opponent['hp'] - before} Health.")
        row["turns"] = int(row["turns"]) - 1
    buffs["opp_regen"] = [r for r in regen if int(r["turns"]) > 0]
    minion = opponent.get("minion") if isinstance(opponent.get("minion"), dict) else None
    if not skipped and minion and int(minion.get("hp") or 0) > 0:
        damage_player(state, int(minion.get("damage") or 0), lines, source=str(minion.get("label")))
    return lines


def end_opponent_turn(state: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    buffs = _buffs(state)
    temps = buffs.get("morale_temp") or []
    keep = []
    for row in temps:
        if int(row.get("age") or 0) >= 1:
            change_morale(state, int(row["amount"]), lines)
            lines.append("Your Morale returns to normal.")
        else:
            row["age"] = 1
            keep.append(row)
    buffs["morale_temp"] = keep
    if int(buffs.get("skip_opponent_after_next_armed") or 0) > 0:
        _inc(buffs, "skip_opponent_turns", int(buffs.pop("skip_opponent_after_next_armed")))
    if int(buffs.get("skip_opponent_after_next") or 0) > 0:
        buffs["skip_opponent_after_next_armed"] = int(buffs.pop("skip_opponent_after_next"))
    tick_timed(state, "opponent")
    return lines


def _apply_opponent_side(
    state: dict[str, Any], tactic: dict[str, Any], lines: list[str], *, draw: Draw | None
) -> None:
    buffs = _buffs(state)
    opponent = state.setdefault("opponent", {})
    label = opponent_label(state)

    damage = int(tactic.get("damage") or 0)
    if tactic.get("damage_from_draw_half") and draw:
        card = draw(1)[0]
        damage = half_up(card_value(card))
        lines.append(f"Drew **{card}** — {label} deals half its value.")
    if str(tactic.get("damage_formula") or "") == "own_hp":
        damage = int(opponent.get("hp") or 0)
    if damage > 0:
        damage += timed_value(state, "opponent_damage_bonus")
        damage_player(state, damage, lines, source=label)
    if int(tactic.get("morale_damage") or 0) > 0:
        amount = int(tactic["morale_damage"])
        before = int(player_state(state)["morale"])
        change_morale(state, -amount, lines)
        lost = before - int(player_state(state)["morale"])
        if tactic.get("morale_temporary") and lost:
            buffs.setdefault("morale_temp", []).append({"amount": lost, "age": 0})
    if tactic.get("skip_turn"):
        _inc(buffs, "skip_player")
        lines.append("You lose your next turn.")
    if int(tactic.get("self_damage") or 0) > 0:
        sd = int(tactic["self_damage"])
        opponent["hp"] = max(0, int(opponent.get("hp") or 0) - sd)
        lines.append(f"{label} takes {sd} damage in its frenzy.")
    if tactic.get("summon_hp"):
        opponent["minion"] = {
            "label": "secondary opponent",
            "hp": int(tactic["summon_hp"]),
            "damage": int(tactic.get("summon_damage") or 0),
        }
        lines.append(
            f"A secondary opponent joins ({tactic['summon_hp']} Health, "
            f"{tactic.get('summon_damage', 0)} damage per opponent turn)."
        )
    if int(tactic.get("heal") or 0) > 0 and not tactic.get("heal_per_turn_turns"):
        before = int(opponent.get("hp") or 0)
        opponent["hp"] = min(int(opponent.get("max_hp") or 20), before + int(tactic["heal"]))
        lines.append(f"{label} heals {opponent['hp'] - before}.")
    if tactic.get("heal_per_turn_turns"):
        buffs.setdefault("opp_regen", []).append(
            {
                "amount": int(tactic.get("heal_per_turn") or tactic.get("heal") or 0),
                "turns": int(tactic["heal_per_turn_turns"]),
            }
        )
    if tactic.get("opponent_halve_next"):
        _inc(buffs, "opponent_halve_next", int(tactic["opponent_halve_next"]))
    if tactic.get("opponent_evades_next") or tactic.get("evade"):
        _inc(buffs, "opponent_evades_next", int(tactic.get("opponent_evades_next") or 1))
    if tactic.get("player_attacks_miss_turns"):
        _inc(buffs, "player_attacks_miss_turns", int(tactic["player_attacks_miss_turns"]))
    if tactic.get("reduce_player_damage"):
        add_timed(
            state,
            "reduce_player_damage",
            int(tactic["reduce_player_damage"]),
            int(tactic.get("reduce_player_damage_turns") or 1),
            created_by="opponent",
        )
    if tactic.get("opponent_armor"):
        add_timed(
            state,
            "opponent_armor",
            int(tactic["opponent_armor"]),
            int(tactic.get("opponent_armor_turns") or 1),
            created_by="opponent",
        )
    if tactic.get("opponent_damage_bonus"):
        add_timed(
            state,
            "opponent_damage_bonus",
            int(tactic["opponent_damage_bonus"]),
            int(tactic.get("opponent_damage_bonus_turns") or 1),
            created_by="opponent",
        )
    if tactic.get("rebirth_half") and not opponent.get("rebirth_used"):
        opponent["rebirth_armed"] = True
        lines.append(f"{label} will be reborn once if defeated.")


def apply_tactic_effects(
    state: dict[str, Any],
    tactic: dict[str, Any] | None,
    *,
    actor: str,
    draw: Draw | None = None,
) -> list[str]:
    """Mutate combat state from a tactic row. Returns log lines."""
    if not tactic:
        return [f"{actor}: no tactic resolved."]
    who = {
        "player": "You",
        "opponent": opponent_label(state),
        "eolan": "Eolan",
        "item": "Item",
    }.get(actor, actor)
    lines: list[str] = [f"**{who}** — {tactic.get('label', tactic.get('effect', '?'))}"]
    if actor == "opponent":
        _apply_opponent_side(state, tactic, lines, draw=draw)
    else:
        _apply_player_side(
            state,
            tactic,
            lines,
            actor_label={"player": "You", "eolan": "Eolan", "item": "Item"}.get(actor, actor),
            use_player_bonuses=actor in ("player", "item"),
            draw=draw,
        )
    return lines
