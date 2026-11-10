"""Auto-update campaign journal (NPCs, locations, log) after each play turn."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.dm.memory_dedupe import looks_like_entity_name, merge_update
from backend.games.dnd5e.prompts import dnd5e_stable_system_prompt
from backend.journal_storage import (
    append_story_arc_note,
    find_journal_entry_id,
    get_campaign,
    get_campaign_location,
    get_campaign_npc,
    list_campaign_locations,
    list_campaign_npcs,
    save_campaign_location,
    save_campaign_npc,
)
from backend.llm import cached_system, structured_llm
from backend.storage import append_adventure_log


class JournalEntryUpdate(BaseModel):
    name: str
    body: str = Field(description="New entry body, or appended update paragraph")


class JournalTurnUpdates(BaseModel):
    new_npcs: list[JournalEntryUpdate] = Field(default_factory=list)
    updated_npcs: list[JournalEntryUpdate] = Field(default_factory=list)
    new_locations: list[JournalEntryUpdate] = Field(default_factory=list)
    updated_locations: list[JournalEntryUpdate] = Field(default_factory=list)
    campaign_note: str = Field(
        default="", description="Major plot beat to append to campaign arc, or empty"
    )
    adventure_log: str = Field(
        default="", description="Extra factual log line if scribe missed something, or empty"
    )


def _name_list(campaign_id: str) -> tuple[list[str], list[str]]:
    npcs = [n["name"] for n in list_campaign_npcs(campaign_id)]
    locs = [loc["name"] for loc in list_campaign_locations(campaign_id)]
    return npcs, locs


_NOTES_PER_ENTRY = 600
_MAX_NOTE_ENTRIES = 6


def _existing_notes(campaign_id: str, turn_text: str) -> str:
    """Current notes for entries named in this turn, so the extractor only adds new facts."""
    lowered = turn_text.lower()
    lines: list[str] = []
    sources = (
        (list_campaign_npcs(campaign_id), "npcs", get_campaign_npc),
        (list_campaign_locations(campaign_id), "locations", get_campaign_location),
    )
    for rows, _kind, getter in sources:
        for row in rows:
            name = str(row.get("name") or "").strip()
            if not name or name.lower() not in lowered:
                continue
            entry = getter(campaign_id, row["id"]) or {}
            body = " ".join(str(entry.get("body") or "").split())
            if body:
                lines.append(f"- {name}: {body[-_NOTES_PER_ENTRY:]}")
            if len(lines) >= _MAX_NOTE_ENTRIES:
                return "\n".join(lines)
    return "\n".join(lines)


def extract_journal_updates(
    *,
    campaign_id: str,
    user_message: str,
    dm_response: str,
) -> JournalTurnUpdates:
    npc_names, loc_names = _name_list(campaign_id)
    notes = _existing_notes(campaign_id, f"{user_message}\n{dm_response}")
    prompt = f"""Analyze this D&D solo play turn and extract journal \
updates ONLY when clearly warranted.

Existing NPCs: {", ".join(npc_names) or "(none)"}
Existing locations: {", ".join(loc_names) or "(none)"}

Current notes for entries mentioned this turn (latest part):
{notes or "(none)"}

Rules:
- new_npcs/new_locations: ONLY for newly introduced NAMED characters
  or places not in existing lists
- updated_npcs/updated_locations: ONLY when status, location,
  or relationship clearly changed for an existing name
- campaign_note: ONLY for major plot revelations (1-3 sentences), else empty string
- adventure_log: ONLY if a critical fact was established and should be recorded, else empty string
- Names must be proper nouns of people, creatures or places. Never use suggested player
  actions or options (for example "Ask Dalla to come with you") as names.
- For updated_* entries, body is ONLY the new fact in 1-2 short sentences. Do not restate
  anything already in the current notes above. If nothing new, leave the entry out.
- Do NOT duplicate entries. Do NOT invent names that were not in the turn.
- Prefer empty lists over speculative entries

Player: {user_message[:1500]}

DM response: {dm_response[:3000]}
"""
    llm = structured_llm(JournalTurnUpdates)
    return llm.invoke(
        [
            cached_system(dnd5e_stable_system_prompt()),
            HumanMessage(content=prompt),
        ]
    )


def _apply_entry_updates(
    *,
    campaign_id: str,
    kind: str,
    new_entries: list[JournalEntryUpdate],
    updated_entries: list[JournalEntryUpdate],
    getter: Callable[[str, str], dict[str, Any] | None],
    saver: Callable[..., Any],
) -> tuple[int, int]:
    """Create or merge entries; names are validated and updates deduped sentence by sentence."""
    created = updated = 0
    for item in [*new_entries, *updated_entries]:
        name = item.name.strip().strip("*").strip()
        if not name or not looks_like_entity_name(name):
            continue
        addition = item.body.strip()
        entry_id = find_journal_entry_id(campaign_id, kind, name)
        if not entry_id:
            saver(campaign_id, None, {"name": name, "body": addition})
            created += 1
            continue
        existing = getter(campaign_id, entry_id) or {}
        if not addition:
            continue
        merged = merge_update(str(existing.get("body") or ""), addition)
        if merged is None:
            continue
        saver(
            campaign_id,
            entry_id,
            {
                "name": existing.get("name", name),
                "body": merged,
                "created_at": existing.get("created_at"),
            },
        )
        updated += 1
    return created, updated


def apply_journal_updates(
    *,
    campaign_id: str,
    adventure_id: str | None,
    updates: JournalTurnUpdates,
) -> dict[str, int]:
    counts = {"new_npcs": 0, "updated_npcs": 0, "new_locations": 0, "updated_locations": 0}

    counts["new_npcs"], counts["updated_npcs"] = _apply_entry_updates(
        campaign_id=campaign_id,
        kind="npcs",
        new_entries=updates.new_npcs,
        updated_entries=updates.updated_npcs,
        getter=get_campaign_npc,
        saver=save_campaign_npc,
    )
    counts["new_locations"], counts["updated_locations"] = _apply_entry_updates(
        campaign_id=campaign_id,
        kind="locations",
        new_entries=updates.new_locations,
        updated_entries=updates.updated_locations,
        getter=get_campaign_location,
        saver=save_campaign_location,
    )

    note = updates.campaign_note.strip()
    if note:
        append_story_arc_note(campaign_id, note)

    log_line = updates.adventure_log.strip()
    if log_line and adventure_id:
        append_adventure_log(adventure_id, log_line)

    return counts


def run_journal_keeper(
    *,
    campaign_id: str | None,
    adventure_id: str | None,
    user_message: str,
    dm_response: str,
) -> dict[str, int]:
    if not campaign_id or not dm_response.strip():
        return {}
    if not get_campaign(campaign_id):
        return {}
    updates = extract_journal_updates(
        campaign_id=campaign_id,
        user_message=user_message,
        dm_response=dm_response,
    )
    return apply_journal_updates(
        campaign_id=campaign_id,
        adventure_id=adventure_id,
        updates=updates,
    )
