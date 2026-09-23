"""Dragonkeep adventure phase state stored in session extras."""

from __future__ import annotations

from typing import Any

from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.dm.curated import (
    _stat_line,
    apply_event_deltas,
    parse_playing_card,
)
from backend.games.brambletrek.modules.combat import (
    combat_preview_from_context,
    eolan_narrative,
    lookup_eolan_ally,
    resolve_dragonkeep_opponent,
)
from backend.games.brambletrek.modules.loader import (
    load_module,
    lookup_module_exploration_row,
    module_path_locations,
)
from backend.games.brambletrek.rag_config import GAME_ID
from backend.play_tools import draw_cards, format_card_result

DRAGONKEEP_ID = "dragonkeep"
DRAGONKEEP_STATE_KEY = "dragonkeep_state"
MAX_PATH_STEP = 7
CAVE_DOOR_STEP = 4  # narrative landmark on the forest path
EXPLORATION_CARDS = 3

PHASES: dict[str, str] = {
    "path": "The Path to Dragonkeep",
    "labyrinth": "The Labyrinth Below",
    "gems": "Room of Gems",
    "exploration": "Elemental Path",
    "antechamber": "Dragonkeep Antechamber",
    "door": "Door of Lunar Light",
    "finale": "Deep Chambers",
}

FINALE_STEPS: dict[str, str] = {
    "meet": "Meet Eolan",
    "door": "Door of Lunar Light",
    "chambers": "The Deep Chambers",
    "dragon": "Battle with Aerith",
    "resolution": "After Aerith",
}

GEMS: dict[str, dict[str, str]] = {
    "path_of_tempest": {
        "label": "Azure Gem — Path of the Tempest",
        "short": "Tempest (water)",
    },
    "path_of_pyre": {
        "label": "Crimson Gem — Path of the Pyre",
        "short": "Pyre (fire)",
    },
    "path_of_leaf": {
        "label": "Verdant Gem — Path of the Leaf",
        "short": "Leaf (forest)",
    },
}


def default_state() -> dict[str, Any]:
    return {
        "phase": "path",
        "path_step": 1,
        "active_gem": "",
        "gems_completed": [],
        "met_eolan": False,
        "door_opened": False,
        "pending_path_card": "",
        "pending_path_outcome": None,
        "path_resolved": False,
        "combat_context": None,
        "finale_step": "meet",
        "finale_phase": "1",
        "eolan_wounded": True,
    }


def _locations(adventure_id: str = DRAGONKEEP_ID) -> dict[str, Any]:
    return module_path_locations(adventure_id)


def _location(step: int, adventure_id: str = DRAGONKEEP_ID) -> dict[str, Any]:
    row = _locations(adventure_id).get(str(step)) or {}
    return dict(row) if isinstance(row, dict) else {}


def _needs_path_draw(step: int, adventure_id: str = DRAGONKEEP_ID) -> bool:
    loc = _location(step, adventure_id)
    return bool(loc.get("suit_outcomes"))


def _phase_label(phase: str) -> str:
    return PHASES.get(phase, phase.replace("_", " ").title())


def _gem_options(state: dict[str, Any]) -> list[dict[str, Any]]:
    done = set(state.get("gems_completed") or [])
    return [
        {
            "id": gem_id,
            "label": meta["label"],
            "short": meta["short"],
            "completed": gem_id in done,
        }
        for gem_id, meta in GEMS.items()
    ]


def _instructions(state: dict[str, Any]) -> str:
    phase = str(state.get("phase") or "path")
    if phase == "path":
        step = int(state.get("path_step") or 1)
        loc = _location(step)
        title = loc.get("title") or f"Location {step}"
        if _needs_path_draw(step) and not state.get("path_resolved"):
            return (
                f"**{title}** — read the scene, then draw a card for what you find "
                f"(♥ ♦ ♣ ♠ table on p. 59–61)."
            )
        if step < MAX_PATH_STEP:
            return f"**{title}** — continue along the forest path when ready."
        return f"**{title}** — enter the cave to descend into the labyrinth."
    if phase == "labyrinth":
        return (
            "You wind through narrow passages into a vast chamber with a pedestal "
            "holding three glowing gems. Proceed to the **Room of Gems**."
        )
    if phase == "gems":
        done = state.get("gems_completed") or []
        if done:
            return (
                "Choose another gem path to explore, or proceed to the **antechamber** "
                "where Eolan waits (p. 70)."
            )
        return "Lift one gem to open an elemental path. Each path takes **3 exploration cards**."
    if phase == "exploration":
        gem = GEMS.get(str(state.get("active_gem") or ""), {})
        return (
            f"Exploring **{gem.get('label', 'the elemental path')}** — draw and resolve "
            f"**{EXPLORATION_CARDS} cards** in the Journey tab, then finish the section."
        )
    if phase == "antechamber":
        body = eolan_narrative("antechamber")
        return body or (
            "Eolan tends his wound beside a makeshift camp. Together you may face the "
            "**Door of Lunar Light** (Oracle relic from Hyhill)."
        )
    if phase == "door":
        body = eolan_narrative("door")
        return (
            body
            or "Place the Oracle's relic in the door slot to open the way to the Deep Chambers."
        )
    if phase == "finale":
        step = str(state.get("finale_step") or "chambers")
        if step == "dragon":
            phase_data = (module_combat_eolan().get("aerith_phases") or {}).get(
                str(state.get("finale_phase") or "1")
            ) or {}
            goal = phase_data.get("goal", "")
            label = phase_data.get("label", "Battle with Aerith")
            rules = eolan_narrative("combat_rules")
            parts = [f"**{label}** — {goal}" if goal else f"**{label}**"]
            if rules:
                parts.append(rules)
            parts.append("Use the **Combat** tab for the automated battle loop.")
            return " ".join(parts)
        if step == "resolution":
            return (
                "Aerith is defeated. Choose whether to free the lunar drake, claim the treasure, "
                "or bargain with Eolan — narrate the aftermath with your DM."
            )
        if step == "door":
            return eolan_narrative("door") or "Approach the Door of Lunar Light with Eolan."
        body = eolan_narrative("chambers") or eolan_narrative("finale")
        return body or (
            "Aerith guards the chained lunar drake. Prepare for the finale battle with Eolan at your side."
        )
    return ""


def module_combat_eolan() -> dict[str, Any]:
    from backend.games.brambletrek.modules.combat import module_combat_config

    return module_combat_config(DRAGONKEEP_ID).get("eolan") or {}


def _available_actions(state: dict[str, Any], *, has_pending_journey: bool) -> list[str]:
    phase = str(state.get("phase") or "path")
    actions: list[str] = []
    if phase == "path":
        step = int(state.get("path_step") or 1)
        if _needs_path_draw(step) and not state.get("path_resolved"):
            if state.get("pending_path_outcome"):
                actions.append("apply_path")
            else:
                actions.append("draw_path")
        else:
            actions.append("advance_path")
    elif phase == "labyrinth":
        actions.append("enter_gems")
    elif phase == "gems":
        actions.extend(["choose_gem_tempest", "choose_gem_pyre", "choose_gem_leaf"])
        if state.get("gems_completed"):
            actions.append("to_antechamber")
    elif phase == "exploration":
        if not has_pending_journey:
            actions.append("start_exploration")
    elif phase == "antechamber":
        actions.append("to_door")
    elif phase == "door":
        actions.append("open_door")
    elif phase == "finale":
        step = str(state.get("finale_step") or "chambers")
        if step == "chambers":
            actions.append("advance_finale")
        elif step == "dragon":
            actions.append("advance_finale_phase")
        elif step == "resolution":
            pass
    return actions


def dragonkeep_payload(
    state: dict[str, Any] | None,
    *,
    has_pending_journey: bool = False,
    adventure_id: str = DRAGONKEEP_ID,
) -> dict[str, Any] | None:
    if not state:
        return None
    phase = str(state.get("phase") or "path")
    step = int(state.get("path_step") or 1)
    loc = _location(step, adventure_id) if phase == "path" else {}
    pending = state.get("pending_path_outcome")
    combat_ctx = state.get("combat_context")
    finale_step = str(state.get("finale_step") or "meet")
    return {
        "phase": phase,
        "phase_label": _phase_label(phase),
        "path_step": step,
        "path_total": MAX_PATH_STEP,
        "location_title": loc.get("title") or "",
        "location_body": loc.get("body") or "",
        "needs_path_draw": phase == "path" and _needs_path_draw(step, adventure_id),
        "path_resolved": bool(state.get("path_resolved")),
        "pending_path_card": state.get("pending_path_card") or "",
        "pending_path_preview": _stat_line(pending) if isinstance(pending, dict) else "",
        "pending_path_label": (pending or {}).get("label") if isinstance(pending, dict) else "",
        "active_gem": state.get("active_gem") or "",
        "active_gem_label": GEMS.get(str(state.get("active_gem") or ""), {}).get("label", ""),
        "gems": _gem_options(state),
        "gems_completed": list(state.get("gems_completed") or []),
        "met_eolan": bool(state.get("met_eolan")),
        "door_opened": bool(state.get("door_opened")),
        "combat_context": combat_ctx if isinstance(combat_ctx, dict) else None,
        "combat_preview": combat_preview_from_context(
            combat_ctx if isinstance(combat_ctx, dict) else None
        ),
        "finale_step": finale_step,
        "finale_step_label": FINALE_STEPS.get(finale_step, finale_step),
        "finale_phase": str(state.get("finale_phase") or "1"),
        "eolan_wounded": bool(state.get("eolan_wounded", True)),
        "instructions": _instructions(state),
        "actions": _available_actions(state, has_pending_journey=has_pending_journey),
        "module_label": load_module(adventure_id).get("label", "Dungeons of Dragonkeep"),
    }


def ensure_dragonkeep_state(extras: dict[str, Any]) -> dict[str, Any]:
    state = extras.get(DRAGONKEEP_STATE_KEY)
    if not isinstance(state, dict) or not state.get("phase"):
        state = default_state()
        extras[DRAGONKEEP_STATE_KEY] = state
    return state


def reset_dragonkeep_state(extras: dict[str, Any]) -> dict[str, Any]:
    state = default_state()
    extras[DRAGONKEEP_STATE_KEY] = state
    return state


def _resolve_path_outcome(
    card: str, step: int, adventure_id: str = DRAGONKEEP_ID
) -> dict[str, Any] | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    loc = _location(step, adventure_id)
    outcomes = loc.get("suit_outcomes") or {}
    row = outcomes.get(parsed["suit"])
    if not isinstance(row, dict):
        return None
    return {**row, "card": card, "suit": parsed["suit"]}


def draw_path_card(
    state: dict[str, Any],
    *,
    char_id: str,
    card_source: str = "virtual",
    adventure_id: str = DRAGONKEEP_ID,
) -> dict[str, Any]:
    phase = str(state.get("phase") or "")
    if phase != "path":
        raise ValueError("Not on the path phase")
    step = int(state.get("path_step") or 1)
    if not _needs_path_draw(step, adventure_id):
        raise ValueError("This location has no card table")
    if state.get("path_resolved"):
        raise ValueError("Already resolved — advance along the path")

    if card_source == "physical":
        return {
            "card": "",
            "message": "Physical deck — draw a card and apply the matching suit outcome.",
        }

    result = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Draw failed")
    card = result["cards"][0]
    outcome = _resolve_path_outcome(card, step, adventure_id)
    if not outcome:
        raise ValueError(f"No outcome for {card} at location {step}")
    state["pending_path_card"] = card
    state["pending_path_outcome"] = outcome
    return {
        "card": card,
        "outcome": outcome,
        "summary": format_card_result(result),
        "preview": _stat_line(outcome),
        "label": outcome.get("label", ""),
    }


def apply_path_outcome(state: dict[str, Any], char: BrambletrekCharacter) -> str:
    if str(state.get("phase") or "") != "path":
        raise ValueError("Not on the path phase")
    outcome = state.get("pending_path_outcome")
    if not isinstance(outcome, dict):
        raise ValueError("Draw a path card first")
    if state.get("path_resolved"):
        raise ValueError("Path outcome already applied")

    notes: list[str] = []
    if outcome.get("combat"):
        notes.append("Combat — use **Combat setup** (no automatic stat change).")
    else:
        apply_event_deltas(char, outcome)
        char.clamp_stats()
        stat = _stat_line(outcome)
        if stat != "—":
            notes.append(stat)

    state["path_resolved"] = True
    label = str(outcome.get("label") or state.get("pending_path_card") or "Outcome")
    return f"**{label}** — " + "; ".join(notes) if notes else f"**{label}**"


def advance_path(state: dict[str, Any], adventure_id: str = DRAGONKEEP_ID) -> dict[str, Any]:
    if str(state.get("phase") or "") != "path":
        raise ValueError("Not on the path phase")
    step = int(state.get("path_step") or 1)
    if _needs_path_draw(step, adventure_id) and not state.get("path_resolved"):
        raise ValueError("Resolve the card draw at this location first")

    if step >= MAX_PATH_STEP:
        state["phase"] = "labyrinth"
    else:
        state["path_step"] = step + 1

    state["path_resolved"] = False
    state["pending_path_card"] = ""
    state["pending_path_outcome"] = None
    return {"phase": state["phase"], "path_step": state.get("path_step")}


def enter_gems(state: dict[str, Any]) -> None:
    if str(state.get("phase") or "") != "labyrinth":
        raise ValueError("Not in the labyrinth")
    state["phase"] = "gems"


def choose_gem(state: dict[str, Any], gem_id: str) -> None:
    if str(state.get("phase") or "") not in ("gems", "exploration"):
        raise ValueError("Not at the Room of Gems")
    if gem_id not in GEMS:
        raise ValueError(f"Unknown gem path: {gem_id}")
    state["phase"] = "exploration"
    state["active_gem"] = gem_id


def exploration_table_id(state: dict[str, Any]) -> str:
    return str(state.get("active_gem") or "")


def start_exploration_cards(
    state: dict[str, Any],
    *,
    char_id: str,
    card_source: str = "virtual",
) -> list[str]:
    if str(state.get("phase") or "") != "exploration":
        raise ValueError("Not on an elemental path")
    table_id = exploration_table_id(state)
    if not table_id:
        raise ValueError("No gem path selected")
    if card_source == "physical":
        raise ValueError("Use virtual deck for exploration batch draw")
    result = draw_cards(count=EXPLORATION_CARDS, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Draw failed")
    return list(result["cards"])


def complete_exploration(state: dict[str, Any]) -> dict[str, Any]:
    if str(state.get("phase") or "") != "exploration":
        raise ValueError("Not on an elemental path")
    gem_id = exploration_table_id(state)
    if not gem_id:
        raise ValueError("No active gem path")
    done = list(state.get("gems_completed") or [])
    if gem_id not in done:
        done.append(gem_id)
    state["gems_completed"] = done
    state["phase"] = "gems"
    state["active_gem"] = ""
    return {"gems_completed": done, "phase": "gems"}


def to_antechamber(state: dict[str, Any]) -> None:
    if str(state.get("phase") or "") != "gems":
        raise ValueError("Not at the Room of Gems")
    if not state.get("gems_completed"):
        raise ValueError("Complete at least one gem path first")
    state["phase"] = "antechamber"
    state["finale_step"] = "meet"
    state["met_eolan"] = True


def to_door(state: dict[str, Any]) -> None:
    if str(state.get("phase") or "") != "antechamber":
        raise ValueError("Not in the antechamber")
    state["phase"] = "door"
    state["finale_step"] = "door"


def open_door(state: dict[str, Any], *, oracle_relic: bool = False) -> None:
    if str(state.get("phase") or "") != "door":
        raise ValueError("Not at the Door of Lunar Light")
    if not oracle_relic:
        raise ValueError(
            "The Door of Lunar Light requires the Oracle's relic from Hyhill. "
            "Enable Oracle relic on your character sheet."
        )
    state["phase"] = "finale"
    state["door_opened"] = True
    state["finale_step"] = "chambers"


def advance_finale(state: dict[str, Any]) -> dict[str, Any]:
    step = str(state.get("finale_step") or "chambers")
    if str(state.get("phase") or "") != "finale":
        raise ValueError("Not in the finale")
    if step == "chambers":
        state["finale_step"] = "dragon"
        state["finale_phase"] = "1"
        state["combat_context"] = {
            "adventure_id": DRAGONKEEP_ID,
            "finale": True,
            "finale_phase": "1",
            "opponent_id": "aerith",
        }
        return {"finale_step": "dragon", "finale_phase": "1"}
    raise ValueError("Nothing to advance in this finale step")


def advance_finale_phase(state: dict[str, Any]) -> dict[str, Any]:
    if str(state.get("finale_step") or "") != "dragon":
        raise ValueError("Not in the Aerith battle")
    phase = int(str(state.get("finale_phase") or "1"))
    if phase >= 3:
        complete_aerith(state)
        return {"finale_step": "resolution", "finale_phase": "3"}
    nxt = str(phase + 1)
    state["finale_phase"] = nxt
    ctx = state.get("combat_context")
    if isinstance(ctx, dict):
        ctx = {**ctx, "finale_phase": nxt}
        state["combat_context"] = ctx
    return {"finale_phase": nxt}


def complete_aerith(state: dict[str, Any]) -> dict[str, Any]:
    """Aerith defeated — move to drake/treasure resolution."""
    state["finale_step"] = "resolution"
    state["aerith_defeated"] = True
    return {"finale_step": "resolution"}


def set_combat_from_exploration(
    state: dict[str, Any],
    *,
    gem_path: str,
    event_card: str,
) -> dict[str, Any]:
    opponent_id = resolve_dragonkeep_opponent(gem_path, event_card)
    if not opponent_id:
        raise ValueError(f"No opponent mapped for {event_card} on {gem_path}")
    ctx = {
        "adventure_id": DRAGONKEEP_ID,
        "gem_path": gem_path,
        "event_card": event_card,
        "opponent_id": opponent_id,
    }
    state["combat_context"] = ctx
    return ctx


def draw_eolan_ally(
    state: dict[str, Any],
    *,
    char_id: str,
    card_source: str = "virtual",
) -> dict[str, Any]:
    if str(state.get("finale_step") or "") != "dragon":
        raise ValueError("Eolan ally draws are only during the Aerith battle")
    phase = str(state.get("finale_phase") or "1")
    if card_source == "physical":
        return {"message": "Draw a card for Eolan's tactic after your turn."}
    result = draw_cards(count=1, game_id=GAME_ID, char_id=char_id)
    if not result.get("ok"):
        raise ValueError(result.get("error") or "Draw failed")
    card = result["cards"][0]
    tactic = lookup_eolan_ally(card, phase=phase)
    if not tactic:
        raise ValueError(f"No Eolan tactic for {card} in phase {phase}")
    return {
        "card": card,
        "tactic": tactic,
        "summary": format_card_result(result),
        "label": tactic.get("label", ""),
    }


def lookup_exploration_event(adventure_id: str, table_id: str, card: str) -> dict[str, Any] | None:
    return lookup_module_exploration_row(adventure_id, table_id, card)


def apply_exploration_event(char: BrambletrekCharacter, event: dict[str, Any]) -> str:
    """Apply one Dragonkeep exploration row."""
    before = (char.health, char.morale, char.supplies)
    if event.get("combat"):
        return f"**{event.get('label', '?')}** — Combat; resolve with **Combat setup**."
    apply_event_deltas(char, event)
    char.clamp_stats()
    after = (char.health, char.morale, char.supplies)
    stat = _stat_line(event)
    notes = [stat] if stat != "—" else []
    notes.append(
        f"Health {before[0]}→{after[0]}, Morale {before[1]}→{after[1]}, Supplies {before[2]}→{after[2]}"
    )
    return f"**{event.get('label', '?')}** — " + "; ".join(notes)
