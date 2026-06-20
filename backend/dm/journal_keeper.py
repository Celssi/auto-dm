"""Auto-update campaign journal (NPCs, locations, log) after each play turn."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

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
from backend.llm import get_langchain_chat_llm
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


def extract_journal_updates(
    *,
    campaign_id: str,
    user_message: str,
    dm_response: str,
) -> JournalTurnUpdates:
    npc_names, loc_names = _name_list(campaign_id)
    prompt = f"""Analyze this D&D solo play turn and extract journal \
updates ONLY when clearly warranted.

Existing NPCs: {", ".join(npc_names) or "(none)"}
Existing locations: {", ".join(loc_names) or "(none)"}

Rules:
- new_npcs/new_locations: ONLY for newly introduced NAMED characters
  or places not in existing lists
- updated_npcs/updated_locations: ONLY when status, location,
  or relationship clearly changed for an existing name
- campaign_note: ONLY for major plot revelations (1-3 sentences), else empty string
- adventure_log: ONLY if a critical fact was established and should be recorded, else empty string
- Do NOT duplicate entries. Do NOT invent names that were not in the turn.
- Prefer empty lists over speculative entries

Player: {user_message[:1500]}

DM response: {dm_response[:3000]}
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(JournalTurnUpdates)
    return llm.invoke([HumanMessage(content=prompt)])


def apply_journal_updates(
    *,
    campaign_id: str,
    adventure_id: str | None,
    updates: JournalTurnUpdates,
) -> dict[str, int]:
    counts = {"new_npcs": 0, "updated_npcs": 0, "new_locations": 0, "updated_locations": 0}

    for npc in updates.new_npcs:
        if not npc.name.strip():
            continue
        save_campaign_npc(campaign_id, None, {"name": npc.name.strip(), "body": npc.body.strip()})
        counts["new_npcs"] += 1

    for npc in updates.updated_npcs:
        if not npc.name.strip():
            continue
        entry_id = find_journal_entry_id(campaign_id, "npcs", npc.name)
        if not entry_id:
            save_campaign_npc(
                campaign_id, None, {"name": npc.name.strip(), "body": npc.body.strip()}
            )
            counts["new_npcs"] += 1
            continue
        existing = get_campaign_npc(campaign_id, entry_id) or {}
        body = existing.get("body", "")
        addition = npc.body.strip()
        if addition and addition not in body:
            save_campaign_npc(
                campaign_id,
                entry_id,
                {
                    "name": existing.get("name", npc.name),
                    "body": f"{body}\n\n[Update]\n{addition}".strip(),
                    "created_at": existing.get("created_at"),
                },
            )
            counts["updated_npcs"] += 1

    for loc in updates.new_locations:
        if not loc.name.strip():
            continue
        save_campaign_location(
            campaign_id, None, {"name": loc.name.strip(), "body": loc.body.strip()}
        )
        counts["new_locations"] += 1

    for loc in updates.updated_locations:
        if not loc.name.strip():
            continue
        entry_id = find_journal_entry_id(campaign_id, "locations", loc.name)
        if not entry_id:
            save_campaign_location(
                campaign_id, None, {"name": loc.name.strip(), "body": loc.body.strip()}
            )
            counts["new_locations"] += 1
            continue
        existing = get_campaign_location(campaign_id, entry_id) or {}
        body = existing.get("body", "")
        addition = loc.body.strip()
        if addition and addition not in body:
            save_campaign_location(
                campaign_id,
                entry_id,
                {
                    "name": existing.get("name", loc.name),
                    "body": f"{body}\n\n[Update]\n{addition}".strip(),
                    "created_at": existing.get("created_at"),
                },
            )
            counts["updated_locations"] += 1

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
