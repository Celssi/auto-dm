"""Shared DM bookkeeping nodes (character, scribe, chronicler, journal)."""

from __future__ import annotations

import re

from backend.dm.audit import character_audit_slice, diff_character_slices, record_audit
from backend.dm.journal_keeper import run_journal_keeper
from backend.dm.lonelog import format_mechanical, format_narrative
from backend.dm.narrator import synthesize_lonelog_summary
from backend.dm.state import DMState, char_from_dict, game_plugin
from backend.dm.story_memory import increment_summary
from backend.games.registry import resolve_game_id
from backend.storage import (
    append_adventure_log,
    append_session_log,
    write_adventure_summary,
)

_MIN_RESPONSE_FOR_BOOKKEEPING = 120


def _rag_direct_tasks(state: DMState) -> frozenset[str]:
    char = state.get("character") or {}
    return game_plugin(char).play.rag_direct_tasks


def character_keeper_node(state: DMState) -> DMState:
    updates = dict(state.get("character_updates") or {})
    if not updates:
        return {}
    before_slice = character_audit_slice(state.get("character") or {})
    char_dict = dict(state.get("character") or {})
    char_dict.update(updates)
    plugin = game_plugin(char_dict)
    char = plugin.rebuild_character(char_from_dict(char_dict))
    after_dict = plugin.character_to_dict(char)
    after_slice = character_audit_slice(after_dict)
    diff = diff_character_slices(before_slice, after_slice)
    if diff:
        record_audit(
            {
                "event": "character_patch",
                "source": "graph",
                "before": before_slice,
                "after": after_slice,
                "diff": diff,
                "detail": {"fields": list(updates.keys()), "inferred": False},
            },
            session_id=state.get("session_id") or None,
        )
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
    if narrative and task not in rag_tasks:
        summary = synthesize_lonelog_summary(narrative, chat_provider="claude")
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
        formatted = format_narrative(resource_line)
        if session_id:
            append_session_log(session_id, formatted)
        lines.append(formatted)
    return {"lonelog_lines": lines, "scribe_log_entry": log_entry}


def chronicler_node(state: DMState) -> DMState:
    if game_plugin(state.get("character")).play.skip_chronicler:
        return {}
    if (state.get("shortcut_result") or {}).get("task") in _rag_direct_tasks(state):
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
    if not _needs_journal_keeper(state):
        return {}
    adventure = state.get("adventure") or {}
    campaign_id = adventure.get("campaign_id")
    adventure_id = adventure.get("id")
    dm_response = state.get("response") or state.get("narrative") or ""
    user_message = state.get("user_message") or ""
    counts = run_journal_keeper(
        campaign_id=campaign_id,
        adventure_id=adventure_id,
        user_message=user_message,
        dm_response=dm_response,
    )
    return {"journal_updates": counts} if counts else {}


def _needs_journal_keeper(state: DMState) -> bool:
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
