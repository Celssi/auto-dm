"""Brambletrek combat manager — initiative, turns, HP."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.combat.effects import apply_tactic_effects, tick_turn_buffs
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
from backend.play_tools import draw_cards

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


def _draw_hand(char_id: str, count: int = 4) -> list[str]:
    result = draw_cards(count=count, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Could not draw tactic hand")
    return list(result["cards"])


def _lookup_player_tactic_row(char: BrambletrekCharacter, card: str) -> dict[str, Any] | None:
    legacy = str(char.legacy or "")
    row = lookup_player_tactic(legacy, card)
    if row:
        return {"label": row.get("effect", ""), "effect": row.get("effect", "")}
    adv = str(char.active_adventure or "")
    play = module_play_config(adv)
    table = str(play.get("tactic_table") or "")
    tactic_legacy = str(play.get("tactic_legacy") or "")
    if table and legacy.lower() == tactic_legacy:
        scene = lookup_module_scene_row(adv, table, card)
        if scene:
            return {
                "label": scene.get("label", ""),
                "damage": scene.get("damage"),
                "heal": scene.get("heal"),
            }
    return None


def _core_tactic_from_card(card: str) -> dict[str, Any] | None:
    from backend.games.brambletrek.dm.curated import _combat_reference

    parsed = parse_playing_card(card)
    if not parsed:
        return None
    band = tactic_band(parsed["rank_key"])
    row = (_combat_reference().get("opponent_tactics") or {}).get(band)
    return dict(row) if isinstance(row, dict) else None


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
    _advance_aerith_phase(state, char_id, lines, reason=f"Phase {state.get('finale_phase')} complete.")


def _resolve_opponent_tactic(state: dict[str, Any], card: str) -> dict[str, Any] | None:
    ctx = state.get("combat_context") or {}
    mode = state.get("mode")
    if mode == "aerith_finale":
        phase = str(state.get("finale_phase") or "1")
        return lookup_aerith_tactic(card, phase=phase)
    opp_id = str((state.get("opponent") or {}).get("id") or "")
    adv = str(ctx.get("adventure_id") or "dragonkeep")
    if opp_id.startswith("core_") or ctx.get("type") == "core":
        from backend.games.brambletrek.dm.curated import _combat_reference

        parsed = parse_playing_card(card)
        if not parsed:
            return None
        band = tactic_band(parsed["rank_key"])
        row = (_combat_reference().get("opponent_tactics") or {}).get(band)
        return dict(row) if isinstance(row, dict) else None
    real_id = str(ctx.get("opponent_id") or opp_id)
    tactic = lookup_opponent_tactic(adv, real_id, card)
    if tactic:
        return tactic
    return _core_tactic_from_card(card)


def begin_combat(
    char: BrambletrekCharacter,
    combat_context: dict[str, Any],
    *,
    char_id: str,
    mode: str = "standard",
) -> dict[str, Any]:
    if not combat_context:
        raise ValueError("No combat context")
    init = draw_cards(count=2, game_id=GAME_ID, char_id=char_id)
    if not init.get("ok"):
        raise ValueError(init.get("error") or "Initiative draw failed")
    p_card, o_card = init["cards"][0], init["cards"][1]
    p_val, o_val = _initiative_value(p_card), _initiative_value(o_card)
    if mode == "aerith_finale":
        first = "opponent"
    elif p_val > o_val:
        first = "player"
    elif o_val > p_val:
        first = "opponent"
    else:
        first = "player"

    opp_meta = _opponent_from_context(
        combat_context, card=str(combat_context.get("card") or o_card)
    )
    hand = _draw_hand(char_id, 4)
    state = default_combat_state()
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
            "player": {"hp": char.health},
            "initiative": {"player_card": p_card, "opponent_card": o_card, "first": first},
            "tactic_hand": hand,
            "turn": first,
            "finale_phase": str(combat_context.get("finale_phase") or "1"),
            "combat_context": combat_context,
            "log": [f"Combat begins vs **{opp_meta['label']}** (HP {opp_meta['health']})."],
        }
    )
    if mode == "aerith_finale":
        state["log"].append("Turn order: Aerith → You → Eolan.")
        state["can_search_item"] = True
    return state


def _check_end(state: dict[str, Any]) -> str | None:
    opp_hp = int((state.get("opponent") or {}).get("hp") or 0)
    player_hp = int((state.get("player") or {}).get("hp") or 0)
    if player_hp <= 0:
        state["status"] = "lost"
        return "You fall — your Gnawborn will reawaken in the deep forest."
    if opp_hp <= 0 and state.get("mode") != "aerith_finale":
        state["status"] = "won"
        return f"You defeat **{(state.get('opponent') or {}).get('label', 'the opponent')}**!"
    return None


def _advance_turn(state: dict[str, Any]) -> None:
    turn = str(state.get("turn") or "opponent")
    mode = state.get("mode")
    if mode == "aerith_finale":
        order = ("opponent", "player", "eolan")
        idx = order.index(turn) if turn in order else 0
        state["turn"] = order[(idx + 1) % 3]
        if state["turn"] == "opponent":
            prog = state.setdefault("phase_progress", {})
            prog["rounds"] = int(prog.get("rounds") or 0) + 1
            tick_turn_buffs(state.setdefault("buffs", {}))
    else:
        state["turn"] = "player" if turn == "opponent" else "opponent"
        if state["turn"] == "opponent":
            prog = state.setdefault("phase_progress", {})
            prog["rounds"] = int(prog.get("rounds") or 0) + 1
            tick_turn_buffs(state.setdefault("buffs", {}))


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

    if action == "opponent_turn":
        if str(state.get("turn")) != "opponent":
            raise ValueError("Not opponent's turn")
        draw = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
        if not draw.get("ok"):
            raise ValueError(draw.get("error") or "Draw failed")
        card = draw["cards"][0]
        state["opponent_last_card"] = card
        tactic = _resolve_opponent_tactic(state, card)
        if tactic:
            band = tactic.get("band") or tactic_band(
                parse_playing_card(card)["rank_key"] if parse_playing_card(card) else "2"
            )
            seen = state.setdefault("phase_progress", {}).setdefault("bands_seen", [])
            if band not in seen:
                seen.append(band)
        lines.extend(apply_tactic_effects(state, tactic, actor="opponent"))
        end = _check_end(state)
        if end:
            lines.append(end)
        else:
            _advance_turn(state)
        return state, lines

    if action == "play_tactic":
        if str(state.get("turn")) != "player":
            raise ValueError("Not your turn")
        if buffs.get("skip_player", 0) > 0:
            buffs["skip_player"] = int(buffs["skip_player"]) - 1
            lines.append("You skip your turn.")
            _advance_turn(state)
            state["buffs"] = buffs
            return state, lines
        hand = list(state.get("tactic_hand") or [])
        if hand_index < 0 or hand_index >= len(hand):
            raise ValueError("Invalid tactic card index")
        card = hand.pop(hand_index)
        state["tactic_hand"] = hand
        tactic = _lookup_player_tactic_row(char, card)
        if not tactic:
            parsed = parse_playing_card(card)
            tactic = {
                "label": f"Legacy tactic ({card})",
                "damage": max(1, _initiative_value(card) // 2),
            }
        elif not tactic.get("damage") and not tactic.get("heal"):
            tactic = {**tactic, "damage": max(1, _initiative_value(card) // 2)}
        lines.append(f"You play **{card}**.")
        lines.extend(apply_tactic_effects(state, tactic, actor="player"))
        char.health = int((state.get("player") or {}).get("hp") or char.health)
        end = _check_end(state)
        if end:
            lines.append(end)
        else:
            _advance_turn(state)
        return state, lines

    if action == "eolan_turn":
        if state.get("mode") != "aerith_finale":
            raise ValueError("Eolan only acts in the Aerith finale")
        if str(state.get("turn")) != "eolan":
            raise ValueError("Not Eolan's turn")
        draw = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
        if not draw.get("ok"):
            raise ValueError(draw.get("error") or "Draw failed")
        card = draw["cards"][0]
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
                    end = _check_end(state)
                    if end:
                        lines.append(end)
                    else:
                        _advance_turn(state)
                    return state, lines
            else:
                prog["eolan_red_streak"] = 0
        else:
            prog["eolan_red_streak"] = 0
        lines.extend(apply_tactic_effects(state, tactic, actor="eolan"))
        _maybe_auto_advance_aerith_phase(state, lines, char_id=char_id)
        end = _check_end(state)
        if end:
            lines.append(end)
        else:
            _advance_turn(state)
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
        draw = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
        if not draw.get("ok"):
            raise ValueError(draw.get("error") or "Draw failed")
        card = draw["cards"][0]
        state["item_used_this_phase"] = True
        parsed = parse_playing_card(card)
        is_red = bool(parsed and parsed.get("suit") in ("hearts", "diamonds"))
        lines.append(f"Item search draw: **{card}** ({'red' if is_red else 'black'}).")
        if not is_red:
            lines.append("Aerith interrupts — you drop the item and lose your turn.")
            buffs["skip_player"] = int(buffs.get("skip_player") or 0) + 1
            state["buffs"] = buffs
            _advance_turn(state)
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
            char.health = int((state.get("player") or {}).get("hp") or char.health)
        _advance_turn(state)
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
        "log": (state.get("log") or [])[-12:],
        "combat_preview": (state.get("opponent") or {}).get("label", ""),
        "item_used_this_phase": bool(state.get("item_used_this_phase")),
        "can_search_item": bool(state.get("can_search_item")),
        "combat_items": list(state.get("combat_items") or []),
        "buffs": state.get("buffs") or {},
    }


def end_combat(state: dict[str, Any]) -> dict[str, Any]:
    state["status"] = "idle"
    return state
