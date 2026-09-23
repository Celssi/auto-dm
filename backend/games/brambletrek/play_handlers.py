"""Brambletrek play logic for auto-dm sessions."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.characters.entity import (
    BrambletrekCharacter,
    apply_legacy_stat_change,
    character_from_dict,
    character_table_band,
    character_to_dict,
    legacy_stat_deltas,
)
from backend.games.brambletrek.characters.resource_creation import (
    RESOURCE_DRAFT_KEY,
)
from backend.games.brambletrek.combat import begin_combat, combat_action, combat_payload, end_combat
from backend.games.brambletrek.combat.state import COMBAT_STATE_KEY
from backend.games.brambletrek.dm.curated import (
    apply_item_effects,
    apply_single_journey_event,
    event_needs_item_draw,
    format_character_table,
    format_item_draw,
    item_effect_preview,
    journey_depths_trace,
    legacy_abilities,
    lookup_item,
    lookup_journey_event,
    overcome_the_odds,
    parse_playing_card,
    reset_daily_legacy_abilities,
)
from backend.games.brambletrek.lonelog import (
    card_short_label,
    format_resources,
    format_scene_header,
    log_draw,
    log_mechanical,
)
from backend.games.brambletrek.modules.combat import (
    build_combat_context,
    combat_preview_from_context,
    lookup_core_opponent,
    lookup_guardian,
)
from backend.games.brambletrek.modules.dragonkeep_state import (
    DRAGONKEEP_ID,
    DRAGONKEEP_STATE_KEY,
    advance_finale,
    advance_finale_phase,
    advance_path,
    apply_exploration_event,
    apply_path_outcome,
    choose_gem,
    complete_exploration,
    dragonkeep_payload,
    draw_eolan_ally,
    draw_path_card,
    ensure_dragonkeep_state,
    enter_gems,
    exploration_table_id,
    lookup_exploration_event,
    open_door,
    reset_dragonkeep_state,
    set_combat_from_exploration,
    start_exploration_cards,
    to_antechamber,
    to_door,
)
from backend.games.brambletrek.rag_config import GAME_ID
from backend.play_tools import draw_cards, format_card_result
from backend.storage import get_character, get_session, save_character, update_session_extras

PENDING_JOURNEY_KEY = "pending_journey"
COMBAT_CONTEXT_KEY = "combat_context"


def get_session_combat_context(session_id: str) -> dict[str, Any] | None:
    extras = _session_extras(session_id)
    ctx = extras.get(COMBAT_CONTEXT_KEY)
    if isinstance(ctx, dict) and ctx:
        return ctx
    dk = extras.get(DRAGONKEEP_STATE_KEY)
    if isinstance(dk, dict):
        dctx = dk.get("combat_context")
        if isinstance(dctx, dict) and dctx:
            return dctx
    return None


def _set_combat_context(session_id: str, extras: dict, ctx: dict[str, Any] | None) -> None:
    if ctx:
        extras[COMBAT_CONTEXT_KEY] = ctx
        dk = extras.get(DRAGONKEEP_STATE_KEY)
        if isinstance(dk, dict):
            dk["combat_context"] = ctx
    else:
        extras.pop(COMBAT_CONTEXT_KEY, None)
        dk = extras.get(DRAGONKEEP_STATE_KEY)
        if isinstance(dk, dict):
            dk["combat_context"] = None


def _char(char_id: str) -> BrambletrekCharacter:
    data = get_character(char_id) or {}
    return character_from_dict(data)


def _save(char_id: str, char: BrambletrekCharacter) -> dict:
    save_character(char_id, character_to_dict(char))
    return get_character(char_id) or {}


def _session_extras(session_id: str) -> dict:
    sess = get_session(session_id) or {}
    return dict(sess.get("extras") or {})


def _set_extras(session_id: str, extras: dict) -> None:
    update_session_extras(session_id, extras)


def character_header(char_id: str) -> dict[str, Any]:
    char = _char(char_id)
    return {
        "name": char.name,
        "health": char.health,
        "morale": char.morale,
        "supplies": char.supplies,
        "journey_day": char.journey_day,
        "legacy": char.legacy,
        "in_aldwund": char.in_aldwund,
        "active_adventure": char.active_adventure,
    }


def persist_character(char_id: str, data: dict) -> dict:
    old = _char(char_id)
    char = character_from_dict(data)
    char.id = char_id
    char.clamp_stats()
    if char.legacy != old.legacy:
        oh, om, os = legacy_stat_deltas(old.legacy)
        nh, nm, ns = legacy_stat_deltas(char.legacy)
        pre_applied = (
            char.health == max(0, min(20, old.health - oh + nh))
            and char.morale == max(0, min(20, old.morale - om + nm))
            and char.supplies == max(0, min(20, old.supplies - os + ns))
        )
        if pre_applied:
            char.legacy_abilities_used = {}
        else:
            apply_legacy_stat_change(char, old.legacy, char.legacy)
    return _save(char_id, char)


def get_play_settings(session_id: str) -> tuple[str, str]:
    extras = _session_extras(session_id)
    return extras.get("story_mode", "player"), extras.get("card_source", "virtual")


def journey_event_stat_preview(event: dict) -> str:
    parts: list[str] = []
    for key, icon in (("health", "Health"), ("morale", "Morale"), ("supplies", "Supplies")):
        val = event.get(key)
        if val is not None and val != 0:
            sign = "+" if int(val) > 0 else ""
            parts.append(f"{icon} {sign}{val}")
    if event.get("all_stats") is not None:
        v = int(event["all_stats"])
        sign = "+" if v > 0 else ""
        parts.append(f"All stats {sign}{v}")
    if event.get("combat"):
        parts.append("Combat")
    for tag in event.get("tags") or []:
        parts.append(f"({tag.upper()})")
    return ", ".join(parts) if parts else "—"


def _resolve_pending_event(
    card: str,
    *,
    adventure_id: str,
    in_depths: bool,
    exploration_table: str = "",
) -> dict[str, Any] | None:
    if exploration_table and adventure_id == DRAGONKEEP_ID:
        return lookup_exploration_event(adventure_id, exploration_table, card)
    return lookup_journey_event(card, in_depths=in_depths, adventure_id=adventure_id)


def stash_pending_journey(
    session_id: str,
    char_id: str,
    run: dict,
    shortcut_id: str,
) -> None:
    cards = run.get("journey_cards")
    if not cards or shortcut_id not in (
        "journey_day",
        "aldwund_day",
        "adventure_scene",
        "dragonkeep_exploration",
    ):
        return
    char = _char(char_id)
    extras = _session_extras(session_id)
    exploration_table = str(run.get("exploration_table") or "")
    extras[PENDING_JOURNEY_KEY] = {
        "cards": cards,
        "applied": [False] * len(cards),
        "item_cards": [None] * len(cards),
        "depths_trace": journey_depths_trace(
            cards,
            start_in_aldwund=char.in_aldwund,
            adventure_id=str(char.active_adventure or ""),
        ),
        "shortcut_id": shortcut_id,
        "adventure_id": str(char.active_adventure or ""),
        "exploration_table": exploration_table,
    }
    _set_extras(session_id, extras)
    log_draw(session_id, cards, label="Journey draw")


def pending_journey_payload(session_id: str, char_id: str) -> dict | None:
    pending = _session_extras(session_id).get(PENDING_JOURNEY_KEY)
    if not pending:
        return None
    char = _char(char_id)
    cards = pending.get("cards") or []
    applied = list(pending.get("applied") or [False] * len(cards))
    adventure_id = str(pending.get("adventure_id") or char.active_adventure or "")
    trace = pending.get("depths_trace") or journey_depths_trace(
        cards,
        start_in_aldwund=bool(char.in_aldwund),
        adventure_id=adventure_id,
    )
    item_cards = pending.get("item_cards") or [None] * len(cards)
    exploration_table = str(pending.get("exploration_table") or "")
    zone_label = "Dragonkeep" if exploration_table else None
    events = []
    for i, card in enumerate(cards):
        in_depths = trace[i] if i < len(trace) else char.in_aldwund
        event = _resolve_pending_event(
            card,
            adventure_id=adventure_id,
            in_depths=in_depths,
            exploration_table=exploration_table,
        )
        item_card = item_cards[i] if i < len(item_cards) else None
        item = lookup_item(item_card) if item_card else None
        zone = zone_label or ("Depths" if in_depths else "Surface")
        item_label = item.get("label") if item else None
        is_combat = bool(event and event.get("combat"))
        combat_preview = ""
        if is_combat:
            try:
                preview_ctx = build_combat_context(
                    adventure_id,
                    card,
                    event,
                    exploration_table=exploration_table,
                )
                combat_preview = combat_preview_from_context(preview_ctx)
            except ValueError:
                if adventure_id == "world_tree":
                    guardian = lookup_guardian("world_tree", card)
                    if guardian:
                        combat_preview = (
                            f"{guardian.get('label', '?')} (HP {guardian.get('health', '?')})"
                        )
                    else:
                        core = lookup_core_opponent(card)
                        combat_preview = f"{core.get('label', '?')} (HP {core.get('health', '?')})"
        events.append(
            {
                "index": i,
                "card": card,
                "zone": zone,
                "applied": applied[i] if i < len(applied) else False,
                "can_apply": i == 0 or (i > 0 and applied[i - 1]),
                "label": event.get("label") if event else None,
                "preview": journey_event_stat_preview(event or {}),
                "needs_item": bool(event and event_needs_item_draw(event)),
                "item_card": item_card,
                "item_label": item_label,
                "item_preview": item_effect_preview(item) if item else None,
                "combat": is_combat,
                "combat_preview": combat_preview,
            }
        )
    return {
        "events": events,
        "shortcut_id": pending.get("shortcut_id"),
        "exploration_table": exploration_table,
    }


def _draw_journey_item_card(
    session_id: str,
    char_id: str,
    char: BrambletrekCharacter,
    pending: dict,
    event_index: int,
    event: dict | None,
) -> str | None:
    """Draw and apply an item card when the event needs one. Returns error text or None."""
    if not event_needs_item_draw(event):
        return None
    cards = pending.get("cards") or []
    item_cards = list(pending.get("item_cards") or [None] * len(cards))
    if event_index < len(item_cards) and item_cards[event_index]:
        return None
    result = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        return result.get("error") or "Could not draw item card"
    item_card = result["cards"][0]
    item_cards[event_index] = item_card
    pending["item_cards"] = item_cards
    item = lookup_item(item_card)
    effect_line = apply_item_effects(char, item) if item else ""
    log_draw(session_id, [item_card], label="Item draw")
    log_mechanical(session_id, format_item_draw(item_card))
    if effect_line and effect_line != "No immediate stat change":
        log_mechanical(session_id, effect_line)
    return None


def draw_journey_item(session_id: str, char_id: str, event_index: int) -> dict:
    extras = _session_extras(session_id)
    pending = extras.get(PENDING_JOURNEY_KEY)
    if not pending:
        raise ValueError("No pending journey")
    cards = pending.get("cards") or []
    applied = list(pending.get("applied") or [False] * len(cards))
    if event_index < 0 or event_index >= len(cards):
        raise ValueError("Invalid event index")
    if not applied[event_index]:
        raise ValueError("Apply the event first before drawing an item")
    exploration_table = str(pending.get("exploration_table") or "")
    char = _char(char_id)
    adventure_id = str(pending.get("adventure_id") or char.active_adventure or "")
    trace = pending.get("depths_trace") or []
    in_depths = trace[event_index] if event_index < len(trace) else char.in_aldwund
    event = _resolve_pending_event(
        cards[event_index],
        adventure_id=adventure_id,
        in_depths=in_depths,
        exploration_table=exploration_table,
    )
    item_error = _draw_journey_item_card(
        session_id,
        char_id,
        char,
        pending,
        event_index,
        event,
    )
    extras[PENDING_JOURNEY_KEY] = pending
    _set_extras(session_id, extras)
    entity = _save(char_id, char)
    return {
        "item_error": item_error,
        "character": entity,
        "header": character_header(char_id),
        "pending_journey": pending_journey_payload(session_id, char_id),
    }


def apply_journey_event(session_id: str, char_id: str, event_index: int) -> dict:
    extras = _session_extras(session_id)
    pending = extras.get(PENDING_JOURNEY_KEY)
    if not pending:
        raise ValueError("No pending journey")
    cards = pending.get("cards") or []
    applied = list(pending.get("applied") or [False] * len(cards))
    trace = pending.get("depths_trace") or []
    if event_index < 0 or event_index >= len(cards):
        raise ValueError("Invalid event index")
    if applied[event_index]:
        raise ValueError("Event already applied")
    if event_index > 0 and not applied[event_index - 1]:
        raise ValueError("Apply previous events first")
    char = _char(char_id)
    adventure_id = str(pending.get("adventure_id") or char.active_adventure or "")
    exploration_table = str(pending.get("exploration_table") or "")
    card = cards[event_index]
    in_depths = trace[event_index] if event_index < len(trace) else char.in_aldwund
    event = _resolve_pending_event(
        card,
        adventure_id=adventure_id,
        in_depths=in_depths,
        exploration_table=exploration_table,
    )
    if exploration_table and event:
        summary = apply_exploration_event(char, event)
    else:
        summary = apply_single_journey_event(
            char, card, in_depths=in_depths, adventure_id=adventure_id
        )
    applied[event_index] = True
    pending["applied"] = applied
    item_error = None
    if event_needs_item_draw(event):
        item_error = _draw_journey_item_card(
            session_id,
            char_id,
            char,
            pending,
            event_index,
            event,
        )
    extras[PENDING_JOURNEY_KEY] = pending
    _set_extras(session_id, extras)
    entity = _save(char_id, char)
    preview = journey_event_stat_preview(event or {})
    log_mechanical(session_id, f"{card_short_label(card)} {preview}")
    log_mechanical(
        session_id,
        format_resources(char.health, char.morale, char.supplies, name=char.name),
    )
    return {
        "summary": summary,
        "item_error": item_error,
        "character": entity,
        "header": character_header(char_id),
        "pending_journey": pending_journey_payload(session_id, char_id),
    }


def finish_journey_day(session_id: str, char_id: str) -> dict:
    char = _char(char_id)
    extras = _session_extras(session_id)
    pending = extras.get(PENDING_JOURNEY_KEY) or {}
    exploration_table = str(pending.get("exploration_table") or "")

    char.journey_day = max(1, char.journey_day + 1)
    reset_daily_legacy_abilities(char)
    char.clamp_stats()
    entity = _save(char_id, char)
    log_mechanical(session_id, format_scene_header(char))
    log_mechanical(
        session_id,
        format_resources(char.health, char.morale, char.supplies, name=char.name),
    )

    if exploration_table and str(char.active_adventure or "") == DRAGONKEEP_ID:
        dk = ensure_dragonkeep_state(extras)
        complete_exploration(dk)
        log_mechanical(session_id, "Returned to the Room of Gems.")

    extras.pop(PENDING_JOURNEY_KEY, None)
    _set_extras(session_id, extras)
    out: dict[str, Any] = {
        "character": entity,
        "header": character_header(char_id),
        "pending_journey": None,
    }
    if str(char.active_adventure or "") == DRAGONKEEP_ID:
        dk = ensure_dragonkeep_state(extras)
        out["dragonkeep"] = dragonkeep_payload(
            dk,
            has_pending_journey=False,
        )
    return out


def discard_journey(session_id: str) -> dict:
    extras = _session_extras(session_id)
    extras.pop(PENDING_JOURNEY_KEY, None)
    _set_extras(session_id, extras)
    return {"pending_journey": None}


def draw_character_table(char_id: str, table: str, session_id: str = "") -> dict:
    if table not in ("reason", "background", "trinket"):
        raise ValueError(f"Unknown table: {table}")
    story_mode, card_source = get_play_settings(session_id) if session_id else ("player", "virtual")
    if card_source == "physical":
        return {
            "card": "",
            "band": "",
            "message": f"Physical deck — draw a card and enter it for {table}.",
        }
    result = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Draw failed")
    card = result["cards"][0]
    parsed = parse_playing_card(card)
    band = character_table_band(parsed["rank_key"]) if parsed else ""
    char = _char(char_id)
    if table == "reason":
        char.reason_card = card
        char.reason_band = band
    elif table == "background":
        char.background_card = card
        char.background_band = band
    else:
        char.trinket_card = card
        char.trinket_band = band
    entity = _save(char_id, char)
    if session_id:
        log_draw(session_id, [card], label=table.title())
    preview = (
        format_character_table(
            table, band, card=card, adventure_id=str(char.active_adventure or "")
        )
        if band
        else ""
    )
    return {
        "card": card,
        "band": band,
        "summary": format_card_result(result),
        "preview": preview,
        "character": entity,
    }


def legacy_abilities_payload(legacy_id: str, used_map: dict[str, bool]) -> list[dict]:
    abilities = []
    for ab in legacy_abilities(legacy_id):
        abilities.append(
            {
                "id": ab["id"],
                "label": ab["label"],
                "description": ab.get("description", ""),
                "tags": ab.get("tags") or [],
                "used": used_map.get(ab["id"], False),
            }
        )
    oto = overcome_the_odds()
    abilities.append(
        {
            "id": oto["id"],
            "label": oto["label"],
            "description": oto.get("description", ""),
            "tags": ["universal"],
            "used": used_map.get(oto["id"], False),
        }
    )
    return abilities


def resource_draft_state(session_id: str) -> dict | None:
    return _session_extras(session_id).get(RESOURCE_DRAFT_KEY)


def set_resource_draft(session_id: str, draft: dict | None) -> None:
    extras = _session_extras(session_id)
    if draft is None:
        extras.pop(RESOURCE_DRAFT_KEY, None)
    else:
        extras[RESOURCE_DRAFT_KEY] = draft
    _set_extras(session_id, extras)


def _dragonkeep_char_check(char: BrambletrekCharacter) -> None:
    if str(char.active_adventure or "") != DRAGONKEEP_ID:
        raise ValueError("Active adventure is not Dungeons of Dragonkeep")


def _dragonkeep_response(session_id: str, char_id: str, extras: dict) -> dict[str, Any]:
    pending = extras.get(PENDING_JOURNEY_KEY)
    dk = ensure_dragonkeep_state(extras)
    _set_extras(session_id, extras)
    return {
        "dragonkeep": dragonkeep_payload(dk, has_pending_journey=bool(pending)),
        "pending_journey": pending_journey_payload(session_id, char_id) if pending else None,
        "header": character_header(char_id),
    }


def get_dragonkeep_state(session_id: str, char_id: str) -> dict[str, Any]:
    char = _char(char_id)
    _dragonkeep_char_check(char)
    extras = _session_extras(session_id)
    ensure_dragonkeep_state(extras)
    _set_extras(session_id, extras)
    return _dragonkeep_response(session_id, char_id, extras)


def init_dragonkeep_state(session_id: str, char_id: str) -> dict[str, Any]:
    char = _char(char_id)
    _dragonkeep_char_check(char)
    extras = _session_extras(session_id)
    reset_dragonkeep_state(extras)
    extras.pop(PENDING_JOURNEY_KEY, None)
    log_mechanical(session_id, "Dragonkeep — began the path through the forest.")
    return _dragonkeep_response(session_id, char_id, extras)


def start_journey_combat(session_id: str, char_id: str, event_index: int) -> dict[str, Any]:
    extras = _session_extras(session_id)
    pending = extras.get(PENDING_JOURNEY_KEY)
    if not pending:
        raise ValueError("No pending journey")
    cards = pending.get("cards") or []
    if event_index < 0 or event_index >= len(cards):
        raise ValueError("Invalid event index")
    char = _char(char_id)
    adventure_id = str(pending.get("adventure_id") or char.active_adventure or "")
    exploration_table = str(pending.get("exploration_table") or "")
    card = cards[event_index]
    trace = pending.get("depths_trace") or []
    in_depths = trace[event_index] if event_index < len(trace) else char.in_aldwund
    event = _resolve_pending_event(
        card,
        adventure_id=adventure_id,
        in_depths=in_depths,
        exploration_table=exploration_table,
    )
    if not event or not event.get("combat"):
        raise ValueError("This event is not a combat encounter")

    if exploration_table and adventure_id == DRAGONKEEP_ID:
        dk = ensure_dragonkeep_state(extras)
        ctx = set_combat_from_exploration(
            dk,
            gem_path=exploration_table,
            event_card=card,
        )
    else:
        ctx = build_combat_context(adventure_id, card, event, exploration_table=exploration_table)

    _set_combat_context(session_id, extras, ctx)
    mode = "aerith_finale" if ctx.get("finale") else "standard"
    combat_state = begin_combat(char, ctx, char_id=char_id, mode=mode)
    extras[COMBAT_STATE_KEY] = combat_state
    _set_extras(session_id, extras)
    preview = combat_preview_from_context(ctx)
    log_mechanical(session_id, f"Combat begins — {preview}")
    out: dict[str, Any] = {
        "combat_context": ctx,
        "combat_preview": preview,
        "combat": combat_payload(combat_state),
        "header": character_header(char_id),
        "pending_journey": pending_journey_payload(session_id, char_id),
    }
    if adventure_id == DRAGONKEEP_ID:
        dk = ensure_dragonkeep_state(extras)
        out["dragonkeep"] = dragonkeep_payload(dk, has_pending_journey=True)
    return out


def get_session_combat(session_id: str) -> dict[str, Any] | None:
    extras = _session_extras(session_id)
    state = extras.get(COMBAT_STATE_KEY)
    if not isinstance(state, dict):
        return None
    return combat_payload(state)


def session_combat_action(
    session_id: str,
    char_id: str,
    action: str,
    *,
    hand_index: int = -1,
) -> dict[str, Any]:
    extras = _session_extras(session_id)
    state = extras.get(COMBAT_STATE_KEY)
    if not isinstance(state, dict) or state.get("status") != "active":
        raise ValueError("No active combat")
    char = _char(char_id)
    state, lines = combat_action(
        state,
        char,
        action,
        char_id=char_id,
        hand_index=hand_index,
    )
    extras[COMBAT_STATE_KEY] = state
    _save(char_id, char)
    if state.get("status") in ("won", "lost"):
        for line in lines:
            log_mechanical(session_id, line.replace("**", ""))
        if state.get("mode") == "aerith_finale" and state.get("status") == "won":
            dk = extras.get(DRAGONKEEP_STATE_KEY)
            if isinstance(dk, dict):
                from backend.games.brambletrek.modules.dragonkeep_state import complete_aerith

                complete_aerith(dk)
        if state.get("status") == "lost":
            log_mechanical(session_id, "Your Gnawborn will reawaken in the deep forest.")
    else:
        for line in lines:
            log_mechanical(session_id, line.replace("**", ""))
    _set_extras(session_id, extras)
    out: dict[str, Any] = {
        "combat": combat_payload(state),
        "header": character_header(char_id),
        "character": get_character(char_id),
        "log": lines,
    }
    dk = extras.get(DRAGONKEEP_STATE_KEY)
    if isinstance(dk, dict):
        out["dragonkeep"] = dragonkeep_payload(
            dk, has_pending_journey=bool(extras.get(PENDING_JOURNEY_KEY))
        )
    return out


def dismiss_session_combat(session_id: str) -> dict[str, Any]:
    extras = _session_extras(session_id)
    state = extras.get(COMBAT_STATE_KEY)
    if isinstance(state, dict):
        extras[COMBAT_STATE_KEY] = end_combat(state)
    _set_extras(session_id, extras)
    return {"combat": combat_payload(extras.get(COMBAT_STATE_KEY))}


def dragonkeep_action(
    session_id: str,
    char_id: str,
    action: str,
    gem: str = "",
    event_index: int = -1,
) -> dict[str, Any]:
    char = _char(char_id)
    _dragonkeep_char_check(char)
    _, card_source = get_play_settings(session_id)
    extras = _session_extras(session_id)
    dk = ensure_dragonkeep_state(extras)
    entity = None
    summary = ""

    if action == "advance_path":
        advance_path(dk)
        log_mechanical(session_id, f"Dragonkeep path — location {dk.get('path_step', '?')}")
    elif action == "draw_path":
        draw = draw_path_card(dk, char_id=char_id, card_source=card_source)
        log_draw(session_id, [draw["card"]], label="Path outcome")
        summary = draw.get("label", "")
    elif action == "apply_path":
        summary = apply_path_outcome(dk, char)
        entity = _save(char_id, char)
        log_mechanical(session_id, summary)
    elif action == "enter_gems":
        enter_gems(dk)
        log_mechanical(session_id, "Entered the Room of Gems.")
    elif action in ("choose_gem_tempest", "choose_gem_pyre", "choose_gem_leaf"):
        gem_map = {
            "choose_gem_tempest": "path_of_tempest",
            "choose_gem_pyre": "path_of_pyre",
            "choose_gem_leaf": "path_of_leaf",
        }
        choose_gem(dk, gem_map[action])
        log_mechanical(session_id, f"Chose {gem_map[action].replace('_', ' ')}.")
    elif action == "choose_gem" and gem:
        choose_gem(dk, gem)
        log_mechanical(session_id, f"Chose {gem.replace('_', ' ')}.")
    elif action == "start_exploration":
        cards = start_exploration_cards(dk, char_id=char_id, card_source=card_source)
        table_id = exploration_table_id(dk)
        extras[PENDING_JOURNEY_KEY] = {
            "cards": cards,
            "applied": [False] * len(cards),
            "item_cards": [None] * len(cards),
            "depths_trace": [False] * len(cards),
            "shortcut_id": "dragonkeep_exploration",
            "adventure_id": DRAGONKEEP_ID,
            "exploration_table": table_id,
        }
        log_draw(session_id, cards, label="Dragonkeep exploration")
    elif action == "to_antechamber":
        to_antechamber(dk)
        log_mechanical(session_id, "Met Eolan in the antechamber.")
    elif action == "to_door":
        to_door(dk)
        log_mechanical(session_id, "Approached the Door of Lunar Light.")
    elif action == "open_door":
        open_door(dk, oracle_relic=char.oracle_relic)
        log_mechanical(session_id, "Opened the door to the Deep Chambers.")
    elif action == "advance_finale":
        fin = advance_finale(dk)
        ctx = dk.get("combat_context") if isinstance(dk.get("combat_context"), dict) else None
        _set_combat_context(session_id, extras, ctx)
        if fin.get("finale_step") == "dragon" and ctx:
            combat_state = begin_combat(char, ctx, char_id=char_id, mode="aerith_finale")
            extras[COMBAT_STATE_KEY] = combat_state
        log_mechanical(session_id, f"Finale — {fin.get('finale_step', 'dragon')}.")
    elif action == "advance_finale_phase":
        fin = advance_finale_phase(dk)
        _set_combat_context(
            session_id,
            extras,
            dk.get("combat_context") if isinstance(dk.get("combat_context"), dict) else None,
        )
        combat_state = extras.get(COMBAT_STATE_KEY)
        if isinstance(combat_state, dict) and combat_state.get("status") == "active":
            combat_state, lines = combat_action(
                combat_state,
                char,
                "advance_phase",
                char_id=char_id,
            )
            extras[COMBAT_STATE_KEY] = combat_state
            for line in lines:
                log_mechanical(session_id, line.replace("**", ""))
        log_mechanical(session_id, f"Aerith battle — phase {fin.get('finale_phase')}.")

    elif action == "start_module_combat":
        if event_index < 0:
            raise ValueError("event_index required for start_module_combat")
        out = start_journey_combat(session_id, char_id, event_index)
        return out
    elif action == "eolan_ally_draw":
        draw = draw_eolan_ally(dk, char_id=char_id, card_source=card_source)
        log_draw(session_id, [draw["card"]], label="Eolan tactic")
        summary = f"**Eolan** — {draw.get('label', '')}"
        out = _dragonkeep_response(session_id, char_id, extras)
        out["summary"] = summary
        out["eolan_tactic"] = draw.get("tactic")
        return out
    elif action == "reset":
        reset_dragonkeep_state(dk)
        extras.pop(PENDING_JOURNEY_KEY, None)
        log_mechanical(session_id, "Dragonkeep progress reset.")
    else:
        raise ValueError(f"Unknown Dragonkeep action: {action}")

    out = _dragonkeep_response(session_id, char_id, extras)
    combat_state = extras.get(COMBAT_STATE_KEY)
    if isinstance(combat_state, dict) and combat_state.get("status") == "active":
        out["combat"] = combat_payload(combat_state)
    if entity:
        out["character"] = entity
    if summary:
        out["summary"] = summary
    return out
