"""Shared DM bookkeeping nodes (character, scribe, chronicler, journal)."""

from __future__ import annotations

import re

from backend.dm.audit import character_audit_slice, diff_character_slices, record_audit
from backend.dm.journal_keeper import run_journal_keeper
from backend.dm.lonelog import format_mechanical, format_narrative, is_empty_spell_warning, strip_markdown
from backend.dm.narration_stream import emit_logs, emit_sheet, emit_world
from backend.dm.state import DMState, char_from_dict, game_plugin
from backend.dm.story_memory import increment_summary
from backend.dm.turn_kind import is_dice_only_turn
from backend.games.registry import resolve_game_id
from backend.storage import (
    append_adventure_log,
    append_session_log,
    write_adventure_summary,
)

_MIN_RESPONSE_FOR_BOOKKEEPING = 120


def _cheap_lonelog_summary(narrative: str) -> str:
    text = re.sub(r"\s+", " ", strip_markdown(narrative or "").strip())
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(parts[:2]).strip()
    if len(summary) > 280:
        clipped = summary[:277].rsplit(" ", 1)[0].rstrip(".,;:")
        summary = clipped + "."
    return summary


def _rag_direct_tasks(state: DMState) -> frozenset[str]:
    char = state.get("character") or {}
    return game_plugin(char).play.rag_direct_tasks


def character_keeper_node(state: DMState) -> DMState:
    updates = dict(state.get("character_updates") or {})
    for private in ("_logs", "_npcs", "_scene_position", "_reaction_prompt"):
        updates.pop(private, None)
    if not updates:
        return {}
    before_slice = character_audit_slice(state.get("character") or {})
    char_dict = dict(state.get("character") or {})
    char_dict.update(updates)
    plugin = game_plugin(char_dict)
    char = plugin.rebuild_character(char_from_dict(char_dict))
    after_dict = plugin.character_to_dict(char)
    from backend.games.registry import preserve_live_resources

    if game_plugin(after_dict).play.preserve_live_resources:
        after_dict = preserve_live_resources(char_dict, after_dict)
        for key in (
            "hp",
            "ac",
            "hit_dice_spent",
            "spell_slots",
            "feature_choices",
            "conditions",
            "concentration",
            "lay_on_hands_remaining",
            "active_effects",
            "heroic_inspiration",
            "inventory",
            "currency",
        ):
            if key in updates:
                after_dict[key] = updates[key] if key != "feature_choices" else {
                    **dict(after_dict.get("feature_choices") or {}),
                    **dict(updates.get("feature_choices") or {}),
                }
        if updates.get("hp") is not None:
            after_dict["hp"] = updates["hp"]
        if updates.get("ac") is not None:
            after_dict["ac"] = updates["ac"]
        if updates.get("hit_dice_spent") is not None:
            after_dict["hit_dice_spent"] = updates["hit_dice_spent"]
        if "conditions" in updates:
            after_dict["conditions"] = list(updates.get("conditions") or [])
        if "concentration" in updates:
            after_dict["concentration"] = updates.get("concentration") or ""
        if updates.get("lay_on_hands_remaining") is not None:
            after_dict["lay_on_hands_remaining"] = updates["lay_on_hands_remaining"]
        if "active_effects" in updates:
            after_dict["active_effects"] = list(updates.get("active_effects") or [])
        if "heroic_inspiration" in updates:
            after_dict["heroic_inspiration"] = bool(updates.get("heroic_inspiration"))
        if "inventory" in updates:
            after_dict["inventory"] = list(updates.get("inventory") or [])
        if "currency" in updates:
            after_dict["currency"] = dict(updates.get("currency") or {})
    after_slice = character_audit_slice(after_dict)
    diff = diff_character_slices(before_slice, after_slice)
    if diff:
        hp_before = before_slice.get("hp")
        hp_after = after_slice.get("hp")
        damage = None
        if isinstance(hp_before, int) and isinstance(hp_after, int) and hp_after < hp_before:
            damage = hp_before - hp_after
        record_audit(
            {
                "event": "character_patch",
                "source": "graph",
                "before": before_slice,
                "after": after_slice,
                "diff": diff,
                "detail": {
                    "fields": list(updates.keys()),
                    "inferred": False,
                    "damage": damage,
                    "notes": list(state.get("resource_log") or []),
                },
            },
            session_id=state.get("session_id") or None,
        )
        emit_logs({"refresh": True})
    cid = after_dict.get("id")
    if cid:
        from backend.storage import LIVE_CHARACTER_KEYS, patch_character

        before_char = state.get("character") or {}
        live_patch = {k: v for k, v in updates.items() if k in after_dict}
        for key in LIVE_CHARACTER_KEYS:
            if after_dict.get(key) != before_char.get(key):
                live_patch[key] = after_dict.get(key)
        after_dict = patch_character(cid, live_patch)
        emit_sheet({"character": after_dict})
    return {"character": after_dict}


def scribe_node(state: DMState) -> DMState:
    session_id = state.get("session_id", "")
    narrative = state.get("narrative") or state.get("response", "")
    mechanics = state.get("mechanics_summary", "")
    rag_tasks = _rag_direct_tasks(state)
    lines: list[str] = []
    log_entry = ""
    if mechanics:
        lines.append(format_mechanical(mechanics))
    task = (state.get("shortcut_result") or {}).get("task")
    resource_log = list(state.get("resource_log") or [])
    rest_logged = any(
        "rest" in str(line).lower() or "hit dice" in str(line).lower() or "1d" in str(line).lower()
        for line in resource_log
    )
    if narrative and task not in rag_tasks and not is_dice_only_turn(state) and not rest_logged:
        summary = _cheap_lonelog_summary(narrative)
        log_entry = summary
        lines.append(format_narrative(summary))
        adventure = state.get("adventure") or {}
        adv_id = adventure.get("id")
        if adv_id:
            append_adventure_log(adv_id, summary)
    for line in lines:
        if session_id:
            append_session_log(session_id, line)
    for resource_line in state.get("resource_log") or []:
        if is_empty_spell_warning(resource_line):
            continue
        formatted = format_narrative(resource_line)
        if session_id:
            append_session_log(session_id, formatted)
        lines.append(formatted)
    if lines:
        emit_logs({"lines": lines, "refresh": True})
    return {"lonelog_lines": lines, "scribe_log_entry": log_entry}


def chronicler_node(state: DMState) -> DMState:
    if is_dice_only_turn(state):
        return {}
    if game_plugin(state.get("character")).play.skip_chronicler:
        return {}
    task = (state.get("shortcut_result") or {}).get("task")
    if task in _rag_direct_tasks(state) or task in ("short_rest", "long_rest", "cast_spell"):
        return {}
    adventure = state.get("adventure") or {}
    adv_id = adventure.get("id")
    if not adv_id:
        return {}
    dm_response = state.get("response") or state.get("narrative") or ""
    if len(dm_response.strip()) < _MIN_RESPONSE_FOR_BOOKKEEPING:
        return {}
    existing = adventure.get("summary") or ""
    updated = increment_summary(
        existing,
        user_message=state.get("user_message") or "",
        dm_response=dm_response,
        log_entry=state.get("scribe_log_entry") or "",
        game_id=resolve_game_id(state.get("character") or {}),
    )
    write_adventure_summary(adv_id, updated)
    adventure = dict(adventure)
    adventure["summary"] = updated
    return {"adventure": adventure}


def journal_keeper_node(state: DMState) -> DMState:
    adventure = state.get("adventure") or {}
    campaign_id = adventure.get("campaign_id")
    adventure_id = adventure.get("id")
    npc_delta = []
    extra = state.get("journal_updates") or {}
    from_delta = False
    if isinstance(extra, dict):
        npc_delta = list(extra.get("npcs") or [])
        from_delta = bool(extra.get("from_delta"))
    extract_from_prose = (not from_delta) and _needs_journal_keeper(state) and not npc_delta
    if from_delta and not npc_delta:
        return {}
    if not npc_delta and not extract_from_prose:
        return {}
    dm_response = state.get("response") or state.get("narrative") or ""
    user_message = state.get("user_message") or ""
    counts = run_journal_keeper(
        campaign_id=campaign_id,
        adventure_id=adventure_id,
        user_message=user_message,
        dm_response=dm_response,
        npc_delta=npc_delta,
        extract_from_prose=extract_from_prose,
    )
    emit_world({"refresh": True, "counts": counts or {}})
    return {"journal_updates": counts} if counts else {}


def _needs_journal_keeper(state: DMState) -> bool:
    if is_dice_only_turn(state):
        return False
    task = (state.get("shortcut_result") or {}).get("task")
    if task in ("short_rest", "long_rest", "cast_spell", "rules_help"):
        return False
    if game_plugin(state.get("character")).play.skip_journal_keeper:
        return False
    adventure = state.get("adventure") or {}
    if not adventure.get("campaign_id"):
        return False
    dm_response = state.get("response") or state.get("narrative") or ""
    if len(dm_response.strip()) < 80:
        return False
    names = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", dm_response)
    return len(names) >= 2


def run_deferred_bookkeeping(payload: dict) -> None:
    """Journal, chronicle, and story update after the player already has the shown reply."""
    state: DMState = {
        "session_id": payload.get("session_id") or "",
        "user_message": payload.get("user_message") or "",
        "response": payload.get("response") or "",
        "narrative": payload.get("response") or "",
        "character": payload.get("character") or {},
        "adventure": payload.get("adventure") or {},
        "shortcut_result": payload.get("shortcut_result") or {},
        "scribe_log_entry": payload.get("scribe_log_entry") or "",
        "story_progress": payload.get("story_progress"),
        "lonelog_lines": payload.get("lonelog_lines") or [],
        "journal_updates": payload.get("journal_updates") or {},
    }
    try:
        chronicler_node(state)
    except Exception:
        pass
    if not game_plugin(state.get("character")).play.skip_story_director:
        try:
            from backend.games.dnd5e.dm.agents.nodes import story_director_update_node

            story_director_update_node(state)
        except Exception:
            pass
    try:
        journal_keeper_node(state)
    except Exception:
        pass
