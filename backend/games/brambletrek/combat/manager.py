"""Brambletrek combat manager — initiative, turns, HP."""

from __future__ import annotations

from typing import Any

from backend.dm.prose_style import sanitize_narration_dashes
from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.effects import (
    MAX_STAT,
    apply_tactic_effects,
    end_opponent_turn,
    opponent_label,
    player_state,
    resolve_opponent_turn_effects,
    start_player_turn,
    tick_timed,
)
from backend.games.brambletrek.combat.smores import (
    lookup_smores_tactic,
    new_smores_ally,
    set_intercept,
    smores_ally,
    smores_present,
    use_daily_ability,
)
from backend.games.brambletrek.combat.state import default_combat_state
from backend.games.brambletrek.dm.curated import lookup_player_tactic, parse_playing_card
from backend.games.brambletrek.modules.combat import (
    lookup_aerith_item,
    lookup_aerith_phase_goals,
    lookup_aerith_tactic,
    lookup_eolan_ally,
    lookup_guardian,
    lookup_opponent,
    lookup_opponent_tactic,
)
from backend.games.brambletrek.modules.combat_data import tactic_band
from backend.games.brambletrek.modules.loader import (
    lookup_module_scene_row,
    module_play_config,
)
from backend.games.brambletrek.rag_config import GAME_ID
from backend.play_tools import draw_cards, reset_deck

COMBAT_CONTEXT_KEY = "combat_context"


def _core_opponent_from_card(card: str) -> dict[str, Any]:
    from backend.games.brambletrek.dm.curated import _combat_reference

    parsed = parse_playing_card(card)
    if not parsed:
        return {"id": "unknown", "label": "Unknown foe", "health": 10}
    data = _combat_reference()
    suits = data.get("opponent_type_by_suit") or {}
    hp_map = data.get("opponent_health_by_rank") or {}
    rk = parsed["rank_key"]
    label = suits.get(parsed["suit"], "Opponent")
    health = int(hp_map.get(rk) or hp_map.get("jack") or 10)
    return {"id": f"core_{parsed['suit']}", "label": label, "health": health, "card": card}


def _opponent_from_context(ctx: dict[str, Any], *, card: str = "") -> dict[str, Any]:
    if ctx.get("type") == "guardian":
        g = ctx.get("guardian") if isinstance(ctx.get("guardian"), dict) else None
        if not g and card:
            g = lookup_guardian("world_tree", card)
        if g:
            return {
                "id": f"guardian_{g.get('suit', '')}_{g.get('rank_key', '')}",
                "label": g.get("label", "Guardian"),
                "health": int(g.get("health") or 10),
            }
    if ctx.get("type") == "core":
        return _core_opponent_from_card(str(ctx.get("card") or card))
    opp_id = str(ctx.get("opponent_id") or "")
    adv = str(ctx.get("adventure_id") or "dragonkeep")
    if opp_id == "aerith" or ctx.get("finale"):
        phase = str(ctx.get("finale_phase") or "1")
        return {"id": "aerith", "label": f"Aerith (phase {phase})", "health": 60, "max_hp": 60}
    row = lookup_opponent(adv, opp_id) if opp_id else None
    if row:
        return {
            "id": opp_id,
            "label": row.get("label", opp_id),
            "health": int(row.get("health") or 10),
        }
    return _core_opponent_from_card(card)


def _initiative_value(card: str) -> int:
    parsed = parse_playing_card(card)
    return int(parsed["numeric_value"]) if parsed else 0


def _draw(char_id: str, count: int = 1) -> list[str]:
    """Draw from the shared deck; reshuffle a fresh deck when it runs short mid-combat."""
    result = draw_cards(count=count, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok") and int(result.get("remaining") or 0) < count:
        reset_deck(GAME_ID, char_id)
        result = draw_cards(count=count, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or result.get("summary") or "Card draw failed")
    return list(result["cards"])


def _draw_hand(char_id: str, count: int = 4) -> list[str]:
    return _draw(char_id, count)


def _lookup_player_tactic_row(char: BrambletrekCharacter, card: str) -> dict[str, Any] | None:
    legacy = str(char.legacy or "")
    row = lookup_player_tactic(legacy, card)
    if row:
        return row
    adv = str(char.active_adventure or "")
    play = module_play_config(adv)
    table = str(play.get("tactic_table") or "")
    tactic_legacy = str(play.get("tactic_legacy") or "")
    if table and legacy.lower() == tactic_legacy:
        scene = lookup_module_scene_row(adv, table, card)
        if scene:
            body = str(scene.get("body") or "")
            return {**scene, "label": f"{scene.get('label', '')}. {body}".strip(". ")}
    return None


def _core_tactic_from_card(card: str) -> dict[str, Any] | None:
    """Core Opponent Tactics (p. 30) are listed per card value 2-10, J, Q, K, A."""
    from backend.games.brambletrek.dm.curated import _combat_reference

    parsed = parse_playing_card(card)
    if not parsed:
        return None
    row = (_combat_reference().get("opponent_tactics") or {}).get(parsed["rank_key"])
    return {**row, "band": parsed["rank_key"], "card": card} if isinstance(row, dict) else None


COMBAT_CONTEXT_KEY = "combat_context"
EOLAN_RED_FACE_RANKS = ("jack", "queen", "king", "ace")
EOLAN_CRITICAL_RANKS = ("ace", "king")


def _is_red_card(card: str) -> bool:
    parsed = parse_playing_card(card)
    return bool(parsed and parsed.get("suit") in ("hearts", "diamonds"))


def _aerith_phase_complete(state: dict[str, Any]) -> bool:
    prog = state.get("phase_progress") or {}
    bands = prog.get("bands_seen") or []
    goals = lookup_aerith_phase_goals(str(state.get("finale_phase") or "1"))
    if len(bands) >= int(goals.get("bands_goal") or 7):
        return True
    if int(prog.get("damage_dealt") or 0) >= int(goals.get("damage_goal") or 20):
        return True
    if int(prog.get("rounds") or 0) >= int(goals.get("rounds_goal") or 4):
        return True
    return False


def _advance_aerith_phase(
    state: dict[str, Any],
    char_id: str,
    lines: list[str],
    *,
    reason: str,
) -> None:
    phase = int(str(state.get("finale_phase") or "1"))
    if phase >= 3:
        state["status"] = "won"
        lines.append("Aerith falls! The lunar drake stirs.")
        return
    nxt = str(phase + 1)
    state["finale_phase"] = nxt
    ctx = dict(state.get("combat_context") or {})
    ctx["finale_phase"] = nxt
    state["combat_context"] = ctx
    state["phase_progress"] = {
        "damage_dealt": 0,
        "rounds": 0,
        "bands_seen": [],
        "eolan_red_streak": 0,
    }
    state["tactic_hand"] = _draw_hand(char_id, 4)
    state["turn"] = "opponent"
    state["item_used_this_phase"] = False
    opp = dict(state.get("opponent") or {})
    opp["label"] = f"Aerith (phase {nxt})"
    state["opponent"] = opp
    lines.append(f"{reason} Aerith enters phase {nxt}. New tactic hand drawn.")


def _maybe_auto_advance_aerith_phase(
    state: dict[str, Any], lines: list[str], *, char_id: str = ""
) -> None:
    if state.get("mode") != "aerith_finale" or state.get("status") != "active":
        return
    if not _aerith_phase_complete(state):
        return
    _advance_aerith_phase(
        state, char_id, lines, reason=f"Phase {state.get('finale_phase')} complete."
    )


def _resolve_opponent_tactic(state: dict[str, Any], card: str) -> dict[str, Any] | None:
    ctx = state.get("combat_context") or {}
    mode = state.get("mode")
    if mode == "aerith_finale":
        phase = str(state.get("finale_phase") or "1")
        return lookup_aerith_tactic(card, phase=phase)
    opp_id = str((state.get("opponent") or {}).get("id") or "")
    adv = str(ctx.get("adventure_id") or "dragonkeep")
    if opp_id.startswith("core_") or ctx.get("type") == "core" or opp_id.startswith("guardian_"):
        return _core_tactic_from_card(card)
    real_id = str(ctx.get("opponent_id") or opp_id)
    tactic = lookup_opponent_tactic(adv, real_id, card)
    if tactic:
        return tactic
    return _core_tactic_from_card(card)


def _is_red_table_combat(ctx: dict[str, Any]) -> bool:
    """Core encounters drawn from a red (Favourable) card always drop an ITEM (p. 8)."""
    if ctx.get("type") != "core":
        return False
    return _is_red_card(str(ctx.get("card") or ""))


def begin_combat(
    char: BrambletrekCharacter,
    combat_context: dict[str, Any],
    *,
    char_id: str,
    mode: str = "standard",
) -> dict[str, Any]:
    if not combat_context:
        raise ValueError("No combat context")
    p_card, o_card = _draw(char_id, 2)
    p_val, o_val = _initiative_value(p_card), _initiative_value(o_card)
    if mode == "aerith_finale":
        first = "opponent"
    elif o_val > p_val:
        first = "opponent"
    else:
        first = "player"

    opp_meta = _opponent_from_context(
        combat_context, card=str(combat_context.get("card") or o_card)
    )
    extra_tactics = max(0, int(getattr(char, "extra_tactics_next_combat", 0) or 0))
    hand_size = 4 + extra_tactics
    hand = _draw_hand(char_id, hand_size)
    state = default_combat_state()
    log = [
        f"Combat begins vs **{opp_meta['label']}** (HP {opp_meta['health']}).",
        f"Initiative: you {p_card} vs {o_card}. "
        + ("You go first." if first == "player" else "The opponent goes first."),
    ]
    if extra_tactics:
        char.extra_tactics_next_combat = 0
        log.append(
            f"Carried boon: drew {extra_tactics} extra tactic "
            f"card{'s' if extra_tactics != 1 else ''} ({hand_size} total)."
        )
    state.update(
        {
            "status": "active",
            "mode": mode,
            "adventure_id": str(combat_context.get("adventure_id") or char.active_adventure or ""),
            "opponent": {
                "id": opp_meta["id"],
                "label": opp_meta["label"],
                "hp": opp_meta["health"],
                "max_hp": opp_meta["health"],
            },
            "player": {
                "hp": char.health,
                "morale": char.morale,
                "supplies": char.supplies,
                "max_hp": MAX_STAT,
                "was_hit": False,
            },
            "initiative": {"player_card": p_card, "opponent_card": o_card, "first": first},
            "tactic_hand": hand,
            "turn": first,
            "round": 1,
            "finale_phase": str(combat_context.get("finale_phase") or "1"),
            "combat_context": combat_context,
            "red_table": _is_red_table_combat(combat_context),
            "log": log,
        }
    )
    buffs = state.setdefault("buffs", {})
    dmg_bonus = max(0, int(getattr(char, "next_combat_damage_bonus", 0) or 0))
    if dmg_bonus:
        char.next_combat_damage_bonus = 0
        buffs.setdefault("damage_bonus_list", []).append({"value": dmg_bonus, "attacks": 99})
        log.append(f"Carried boon: +{dmg_bonus} damage this combat.")
    dmg_reduce = max(0, int(getattr(char, "next_combat_damage_reduction", 0) or 0))
    if dmg_reduce:
        char.next_combat_damage_reduction = 0
        buffs.setdefault("reduce_incoming_list", []).append({"value": dmg_reduce, "attacks": 99})
        log.append(f"Carried boon: take {dmg_reduce} less damage per hit this combat.")
    if mode == "aerith_finale":
        state["log"].append("Turn order: Aerith → You → Eolan.")
        state["can_search_item"] = True
    elif str(combat_context.get("ally") or "") == "smores":
        hand = _draw_hand(char_id, 4)
        state["ally"] = new_smores_ally(
            hand=hand,
            daily_used=str(combat_context.get("smores_daily_used") or ""),
        )
        state["smores_daily_used"] = state["ally"]["daily_used"]
        first_note = (
            "the opponent still won initiative, then you, then Smores"
            if first == "opponent"
            else "you, then Smores, then the opponent"
        )
        state["log"].append(
            "Smores joins you as an ally (CDE p. 110). "
            f"Turn order: {first_note}. Draw and play his tactics as if he is another player."
        )
    return state


def _sync_char(state: dict[str, Any], char: BrambletrekCharacter) -> None:
    p = player_state(state)
    char.health = max(0, min(MAX_STAT, int(p["hp"])))
    char.morale = max(0, min(MAX_STAT, int(p["morale"])))
    delta = int(p.pop("supplies_delta", 0) or 0)
    if delta:
        char.supplies = max(0, min(MAX_STAT, int(char.supplies) + delta))


def _check_end(state: dict[str, Any]) -> str | None:
    opp_hp = int((state.get("opponent") or {}).get("hp") or 0)
    p = player_state(state)
    if int(p["hp"]) <= 0:
        state["status"] = "lost"
        state["defeat_stat"] = "health"
        return "You fall — Health reached 0. You are forced to retreat (Health Recovery, p. 16)."
    if int(p["morale"]) <= 0:
        state["status"] = "lost"
        state["defeat_stat"] = "morale"
        return "Your Morale breaks — Morale reached 0 and you flee (Morale Recovery, p. 16)."
    if opp_hp <= 0 and state.get("mode") != "aerith_finale":
        state["status"] = "won"
        msg = f"You defeat **{opponent_label(state)}**!"
        if state.get("red_table") or state.get("steal_item"):
            state["reward_item"] = True
            msg += " You earn an ITEM reward."
        return msg
    return None


def _begin_player_turn(state: dict[str, Any], lines: list[str]) -> None:
    """Start-of-turn effects; auto-resolve a lost turn; flag an empty hand (new round)."""
    while state.get("status") == "active" and str(state.get("turn")) == "player":
        lines.extend(start_player_turn(state))
        end = _check_end(state)
        if end:
            lines.append(end)
            return
        buffs = state.setdefault("buffs", {})
        if int(buffs.get("skip_player") or 0) > 0:
            buffs["skip_player"] = int(buffs["skip_player"]) - 1
            if buffs["skip_player"] <= 0:
                buffs.pop("skip_player", None)
            lines.append("You lose this turn.")
            tick_timed(state, "player")
            _advance_turn(state, lines)
            return
        if not state.get("tactic_hand") and not state.get("must_discard"):
            state["needs_new_round"] = True
            lines.append(
                "You are out of tactic cards: retreat, or draw 4 new cards for the next round."
            )
        return


def _advance_turn(state: dict[str, Any], lines: list[str] | None = None) -> None:
    lines = lines if lines is not None else state.setdefault("log", [])
    turn = str(state.get("turn") or "opponent")
    mode = state.get("mode")
    if mode == "aerith_finale":
        order = ("opponent", "player", "eolan")
    elif smores_present(state):
        first = str((state.get("initiative") or {}).get("first") or "player")
        if first == "opponent":
            order = ("opponent", "player", "smores")
        else:
            order = ("player", "smores", "opponent")
    else:
        order = ("player", "opponent")
    idx = order.index(turn) if turn in order else 0
    state["turn"] = order[(idx + 1) % len(order)]
    if state["turn"] == "opponent":
        prog = state.setdefault("phase_progress", {})
        prog["rounds"] = int(prog.get("rounds") or 0) + 1
    if state["turn"] == "player":
        _begin_player_turn(state, lines)
    elif state["turn"] == "smores":
        _begin_smores_turn(state, lines)


def _finish_player_action(
    state: dict[str, Any], char: BrambletrekCharacter, lines: list[str]
) -> None:
    _sync_char(state, char)
    end = _check_end(state)
    if end:
        lines.append(end)
        return
    tick_timed(state, "player")
    buffs = state.setdefault("buffs", {})
    if int(buffs.get("extra_turns") or 0) > 0:
        buffs["extra_turns"] = int(buffs["extra_turns"]) - 1
        if buffs["extra_turns"] <= 0:
            buffs.pop("extra_turns", None)
        lines.append("You take another turn.")
        _begin_player_turn(state, lines)
        return
    _advance_turn(state, lines)


def _apply_hand_effects(
    state: dict[str, Any], tactic: dict[str, Any], char_id: str, lines: list[str]
) -> None:
    """Tactic effects that change the hand or turn order (pp. 31-32)."""
    buffs = state.setdefault("buffs", {})
    hand = list(state.get("tactic_hand") or [])
    if tactic.get("pick_from_draw"):
        # Tracking: draw two, use one now, discard the other.
        drawn = _draw(char_id, int(tactic["pick_from_draw"]))
        hand.extend(drawn)
        state["must_discard"] = len(drawn) - 1
        state["discard_pool"] = drawn
        if tactic.get("pick_extra_turn", True):
            buffs["extra_turns"] = int(buffs.get("extra_turns") or 0) + 1
            lines.append(f"Drew {', '.join(drawn)} — keep one and play it now.")
        else:
            lines.append(f"Drew {', '.join(drawn)} — keep one in your hand, discard the rest.")
    elif tactic.get("replace_hand"):
        # Masterful Performance: draw 3, replace any number of cards in hand.
        drawn = _draw(char_id, int(tactic.get("draw_tactics") or 3))
        hand.extend(drawn)
        state["must_discard"] = len(drawn)
        state["discard_pool"] = None
        lines.append(
            f"Drew {', '.join(drawn)} — discard {len(drawn)} cards to keep your best hand."
        )
    elif tactic.get("draw_tactics"):
        drawn = _draw(char_id, int(tactic["draw_tactics"]))
        hand.extend(drawn)
        lines.append(f"Drew extra tactic card(s): {', '.join(drawn)}.")
        if tactic.get("discard_after_draw"):
            state["must_discard"] = int(tactic["discard_after_draw"])
            state["discard_pool"] = None
            lines.append("Discard a card from your hand.")
    state["tactic_hand"] = hand
    if tactic.get("extra_turns"):
        buffs["extra_turns"] = int(buffs.get("extra_turns") or 0) + int(tactic["extra_turns"])
    if tactic.get("steal_draw"):
        card = _draw(char_id, 1)[0]
        parsed = parse_playing_card(card)
        if parsed and parsed["rank_key"] in ("jack", "queen", "king", "ace"):
            state["steal_item"] = True
            lines.append(f"Steal draw **{card}** — you will gain an item after combat.")
        else:
            lines.append(f"Steal draw **{card}** — nothing worth taking.")


def _opponent_turn(state: dict[str, Any], char_id: str, lines: list[str]) -> None:
    buffs = state.setdefault("buffs", {})
    label = opponent_label(state)
    if int(buffs.get("skip_opponent_turns") or 0) > 0:
        buffs["skip_opponent_turns"] = int(buffs["skip_opponent_turns"]) - 1
        if buffs["skip_opponent_turns"] <= 0:
            buffs.pop("skip_opponent_turns", None)
        lines.append(f"{label} loses its turn.")
        lines.extend(resolve_opponent_turn_effects(state, skipped=True))
        return
    buffs.pop("skip_opponent_effects", None)
    card = _draw(char_id, 1)[0]
    tactic = _resolve_opponent_tactic(state, card)
    opp = state.get("opponent") or {}
    if (
        tactic
        and tactic.get("rebirth_half")
        and (opp.get("rebirth_used") or opp.get("rebirth_armed"))
    ):
        lines.append(f"Drew **{card}** — Rebirth already used; redrawing.")
        card = _draw(char_id, 1)[0]
        tactic = _resolve_opponent_tactic(state, card)
    state["opponent_last_card"] = card
    lines.append(f"Opponent tactic card: **{card}**.")
    if tactic:
        parsed = parse_playing_card(card)
        band = tactic.get("band") or tactic_band(parsed["rank_key"] if parsed else "2")
        seen = state.setdefault("phase_progress", {}).setdefault("bands_seen", [])
        if band not in seen:
            seen.append(band)
    lines.extend(
        apply_tactic_effects(state, tactic, actor="opponent", draw=lambda n: _draw(char_id, n))
    )
    lines.extend(resolve_opponent_turn_effects(state, skipped=False))


def _begin_smores_turn(state: dict[str, Any], lines: list[str]) -> None:
    if not smores_present(state):
        return
    ally = smores_ally(state)
    if not ally.get("hand"):
        ally["needs_new_round"] = True
        lines.append("Smores is out of tactic cards: draw 4 new cards for him to play.")


def _finish_smores_action(
    state: dict[str, Any], char: BrambletrekCharacter, lines: list[str]
) -> None:
    _sync_char(state, char)
    end = _check_end(state)
    if end:
        lines.append(end)
        return
    ally = smores_ally(state)
    if int(ally.get("extra_turns") or 0) > 0:
        ally["extra_turns"] = int(ally["extra_turns"]) - 1
        if ally["extra_turns"] <= 0:
            ally["extra_turns"] = 0
        lines.append("Smores takes another action.")
        _begin_smores_turn(state, lines)
        return
    _advance_turn(state, lines)
    if str(state.get("turn")) == "smores":
        _begin_smores_turn(state, lines)


def combat_action(
    state: dict[str, Any],
    char: BrambletrekCharacter,
    action: str,
    *,
    char_id: str,
    hand_index: int = -1,
) -> tuple[dict[str, Any], list[str]]:
    if state.get("status") != "active":
        raise ValueError("No active combat")
    lines: list[str] = []
    buffs = state.setdefault("buffs", {})
    player_state(state).setdefault("morale", char.morale)

    if action == "opponent_turn":
        if str(state.get("turn")) != "opponent":
            raise ValueError("Not opponent's turn")
        _opponent_turn(state, char_id, lines)
        lines.extend(end_opponent_turn(state))
        _sync_char(state, char)
        end = _check_end(state)
        if end:
            lines.append(end)
        else:
            _maybe_auto_advance_aerith_phase(state, lines, char_id=char_id)
            _advance_turn(state, lines)
        _sync_char(state, char)
        return state, lines

    if action == "retreat":
        if str(state.get("turn")) != "player":
            raise ValueError("You can only retreat on your turn")
        state["status"] = "retreated"
        state["needs_new_round"] = False
        lines.append(f"You retreat from {opponent_label(state)}.")
        _sync_char(state, char)
        return state, lines

    if action == "new_round":
        if str(state.get("turn")) != "player":
            raise ValueError("Not your turn")
        if state.get("tactic_hand"):
            raise ValueError("You still have tactic cards")
        state["tactic_hand"] = _draw_hand(char_id, 4)
        state["needs_new_round"] = False
        state["round"] = int(state.get("round") or 1) + 1
        lines.append(f"Round {state['round']}: you draw 4 new tactic cards.")
        return state, lines

    if action == "discard_tactic":
        if int(state.get("must_discard") or 0) <= 0:
            raise ValueError("Nothing to discard")
        hand = list(state.get("tactic_hand") or [])
        if hand_index < 0 or hand_index >= len(hand):
            raise ValueError("Invalid tactic card index")
        pool = state.get("discard_pool")
        if pool and hand[hand_index] not in pool:
            raise ValueError("Discard one of the cards you just drew")
        card = hand.pop(hand_index)
        state["tactic_hand"] = hand
        state["must_discard"] = int(state["must_discard"]) - 1
        if state["must_discard"] <= 0:
            state.pop("must_discard", None)
            state.pop("discard_pool", None)
        lines.append(f"You discard {card}.")
        return state, lines

    if action == "play_tactic":
        if str(state.get("turn")) != "player":
            raise ValueError("Not your turn")
        if int(state.get("must_discard") or 0) > 0:
            raise ValueError("Discard the extra card(s) first")
        if state.get("needs_new_round"):
            raise ValueError("Out of cards: retreat or draw a new round")
        hand = list(state.get("tactic_hand") or [])
        if hand_index < 0 or hand_index >= len(hand):
            raise ValueError("Invalid tactic card index")
        card = hand.pop(hand_index)
        state["tactic_hand"] = hand
        tactic = _lookup_player_tactic_row(char, card)
        if not tactic:
            raise ValueError(f"No tactic for {card}: choose a Legacy on the character sheet first.")
        lines.append(f"You play **{card}**.")
        lines.extend(
            apply_tactic_effects(state, tactic, actor="player", draw=lambda n: _draw(char_id, n))
        )
        _apply_hand_effects(state, tactic, char_id, lines)
        _finish_player_action(state, char, lines)
        return state, lines

    if action == "play_smores_tactic":
        if not smores_present(state):
            raise ValueError("Smores is not in this fight")
        if str(state.get("turn")) != "smores":
            raise ValueError("Not Smores' turn")
        ally = smores_ally(state)
        if ally.get("needs_new_round"):
            raise ValueError("Smores is out of cards: draw a new round first")
        hand = list(ally.get("hand") or [])
        if hand_index < 0 or hand_index >= len(hand):
            raise ValueError("Invalid Smores tactic card index")
        card = hand.pop(hand_index)
        ally["hand"] = hand
        tactic = lookup_smores_tactic(card)
        if not tactic:
            raise ValueError(f"No Smores tactic for {card}")
        lines.append(f"Smores plays **{card}**.")
        lines.extend(
            apply_tactic_effects(state, tactic, actor="smores", draw=lambda n: _draw(char_id, n))
        )
        if tactic.get("extra_turns"):
            ally["extra_turns"] = int(ally.get("extra_turns") or 0) + int(tactic["extra_turns"])
        _finish_smores_action(state, char, lines)
        return state, lines

    if action == "smores_new_round":
        if not smores_present(state):
            raise ValueError("Smores is not in this fight")
        if str(state.get("turn")) != "smores":
            raise ValueError("Not Smores' turn")
        ally = smores_ally(state)
        if ally.get("hand"):
            raise ValueError("Smores still has tactic cards")
        ally["hand"] = _draw_hand(char_id, 4)
        ally["needs_new_round"] = False
        lines.append("Smores draws 4 new tactic cards.")
        return state, lines

    if action == "smores_shield":
        lines.extend(use_daily_ability(state, "shield", target="player"))
        _sync_char(state, char)
        return state, lines

    if action == "smores_shield_self":
        lines.extend(use_daily_ability(state, "shield", target="smores"))
        _sync_char(state, char)
        return state, lines

    if action == "smores_sweet_treat":
        lines.extend(use_daily_ability(state, "sweet_treat"))
        _sync_char(state, char)
        end = _check_end(state)
        if end:
            lines.append(end)
        return state, lines

    if action == "smores_intercept":
        ally = smores_ally(state) if smores_present(state) else {}
        lines.extend(set_intercept(state, not bool(ally.get("intercept_next"))))
        return state, lines

    if action == "eolan_turn":
        if state.get("mode") != "aerith_finale":
            raise ValueError("Eolan only acts in the Aerith finale")
        if str(state.get("turn")) != "eolan":
            raise ValueError("Not Eolan's turn")
        card = _draw(char_id, 1)[0]
        phase = str(state.get("finale_phase") or "1")
        tactic = lookup_eolan_ally(card, phase=phase)
        parsed = parse_playing_card(card)
        prog = state.setdefault("phase_progress", {})
        if parsed and _is_red_card(card):
            rank = str(parsed.get("rank_key") or "")
            if rank in EOLAN_RED_FACE_RANKS:
                streak = int(prog.get("eolan_red_streak") or 0) + 1
                prog["eolan_red_streak"] = streak
                if rank in EOLAN_CRITICAL_RANKS:
                    buffs["critical"] = True
                    lines.append("Critical Chance! Your next damaging tactic deals double damage.")
                if streak >= 2:
                    lines.append("Two red face cards in a row — phase complete!")
                    _advance_aerith_phase(
                        state,
                        char_id,
                        lines,
                        reason="Eolan's fortune turns the tide.",
                    )
                    _sync_char(state, char)
                    end = _check_end(state)
                    if end:
                        lines.append(end)
                    else:
                        _advance_turn(state, lines)
                    return state, lines
            else:
                prog["eolan_red_streak"] = 0
        else:
            prog["eolan_red_streak"] = 0
        lines.extend(apply_tactic_effects(state, tactic, actor="eolan"))
        _maybe_auto_advance_aerith_phase(state, lines, char_id=char_id)
        _sync_char(state, char)
        end = _check_end(state)
        if end:
            lines.append(end)
        else:
            _advance_turn(state, lines)
        return state, lines

    if action == "advance_phase":
        if state.get("mode") != "aerith_finale":
            raise ValueError("Not in Aerith finale")
        if not _aerith_phase_complete(state):
            raise ValueError("Phase goals not yet met")
        _advance_aerith_phase(state, char_id, lines, reason="You press the advantage.")
        return state, lines

    if action == "search_item":
        if state.get("mode") != "aerith_finale":
            raise ValueError("Item search only during the Aerith finale")
        if str(state.get("turn")) != "player":
            raise ValueError("Search for items on your turn")
        if state.get("item_used_this_phase"):
            raise ValueError("Already searched for an item this phase")
        card = _draw(char_id, 1)[0]
        state["item_used_this_phase"] = True
        parsed = parse_playing_card(card)
        is_red = bool(parsed and parsed.get("suit") in ("hearts", "diamonds"))
        lines.append(f"Item search draw: **{card}** ({'red' if is_red else 'black'}).")
        if not is_red:
            lines.append("Aerith interrupts — you drop the item and lose your turn.")
            _finish_player_action(state, char, lines)
            return state, lines
        phase = str(state.get("finale_phase") or "1")
        item = lookup_aerith_item(card, phase=phase)
        if not item:
            lines.append("No item matched that card band.")
        else:
            items = list(state.get("combat_items") or [])
            items.append(str(item.get("label") or card))
            state["combat_items"] = items
            lines.extend(apply_tactic_effects(state, item, actor="item"))
        _finish_player_action(state, char, lines)
        return state, lines

    raise ValueError(f"Unknown combat action: {action}")


def combat_payload(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not state or state.get("status") == "idle":
        return None
    phase = str(state.get("finale_phase") or "1")
    goals = lookup_aerith_phase_goals(phase) if state.get("mode") == "aerith_finale" else {}
    phase_complete = (
        _aerith_phase_complete(state) if state.get("mode") == "aerith_finale" else False
    )
    return {
        "status": state.get("status"),
        "mode": state.get("mode"),
        "opponent": state.get("opponent"),
        "player": state.get("player"),
        "initiative": state.get("initiative"),
        "tactic_hand": state.get("tactic_hand") or [],
        "turn": state.get("turn"),
        "finale_phase": state.get("finale_phase"),
        "phase_progress": state.get("phase_progress"),
        "phase_goals": goals or None,
        "phase_complete": phase_complete,
        "can_advance_phase": bool(
            state.get("mode") == "aerith_finale"
            and state.get("status") == "active"
            and phase_complete
        ),
        "log": [sanitize_narration_dashes(line) for line in (state.get("log") or [])[-12:]],
        "combat_preview": (state.get("opponent") or {}).get("label", ""),
        "item_used_this_phase": bool(state.get("item_used_this_phase")),
        "can_search_item": bool(state.get("can_search_item")),
        "combat_items": list(state.get("combat_items") or []),
        "buffs": state.get("buffs") or {},
        "round": int(state.get("round") or 1),
        "needs_new_round": bool(state.get("needs_new_round")),
        "must_discard": int(state.get("must_discard") or 0),
        "discard_pool": state.get("discard_pool") or None,
        "red_table": bool(state.get("red_table")),
        "reward_item": state.get("reward_item") or None,
        "recovery": state.get("recovery") or None,
        "defeat_stat": state.get("defeat_stat") or None,
        "ally": state.get("ally") if smores_present(state) else None,
        "smores_daily_used": (
            str((state.get("ally") or {}).get("daily_used") or "") if smores_present(state) else ""
        ),
    }


def end_combat(state: dict[str, Any]) -> dict[str, Any]:
    state["status"] = "idle"
    return state
