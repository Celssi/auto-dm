"""Encountered NPCs and locations for the play-view roster."""

from __future__ import annotations

import re
from typing import Any

from backend.dm.journal_keeper import (
    JournalTurnUpdates,
    apply_journal_updates,
    extract_journal_updates,
)
from backend.journal_storage import (
    get_campaign,
    get_campaign_location,
    get_campaign_npc,
    list_campaign_entities,
    list_campaign_locations,
    list_campaign_npcs,
)
from backend.storage import (
    get_adventure,
    get_session,
    get_session_world_cache,
    save_session_world_cache,
)

_MARKDOWN_NAME = re.compile(r"\*\*([A-Z][A-Za-z][A-Za-z' -]{1,40})\*\*")
_COMMON_FALSE_POSITIVES = {
    "the",
    "and",
    "you",
    "your",
    "dm",
    "ok",
    "yes",
    "no",
}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _campaign_id_for_session(session: dict[str, Any]) -> str:
    adv_id = str(session.get("adventure_id") or "").strip()
    if not adv_id:
        return ""
    adventure = get_adventure(adv_id) or {}
    return str(adventure.get("campaign_id") or "").strip()


def _entry(kind: str, name: str, body: str = "", source: str = "session") -> dict[str, str]:
    return {
        "kind": kind,
        "name": name.strip(),
        "body": (body or "").strip(),
        "source": source,
    }


def _merge_entries(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_name: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        key = _norm(name)
        if key not in by_name:
            by_name[key] = {
                "kind": str(row.get("kind") or "npc"),
                "name": name,
                "body": str(row.get("body") or "").strip(),
                "source": str(row.get("source") or "session"),
            }
            order.append(key)
            continue
        existing = by_name[key]
        body = str(row.get("body") or "").strip()
        if body and (not existing["body"] or len(body) > len(existing["body"])):
            existing["body"] = body
        if row.get("source") == "campaign":
            existing["source"] = "campaign"
            existing["name"] = name
    return [by_name[key] for key in order]


def campaign_world_entries(campaign_id: str) -> list[dict[str, str]]:
    if not campaign_id or not get_campaign(campaign_id):
        return []
    entries: list[dict[str, str]] = []
    for row in list_campaign_entities(campaign_id):
        kind = str(row.get("kind") or "")
        if kind not in {"npc", "location"}:
            continue
        entries.append(
            _entry(kind, str(row.get("name") or ""), str(row.get("body") or ""), "campaign")
        )
    if entries:
        return entries
    for row in list_campaign_npcs(campaign_id):
        npc = get_campaign_npc(campaign_id, row["id"]) or {}
        entries.append(
            _entry(
                "npc",
                str(npc.get("name") or row.get("name") or ""),
                str(npc.get("body") or ""),
                "campaign",
            )
        )
    for row in list_campaign_locations(campaign_id):
        loc = get_campaign_location(campaign_id, row["id"]) or {}
        entries.append(
            _entry(
                "location",
                str(loc.get("name") or row.get("name") or ""),
                str(loc.get("body") or ""),
                "campaign",
            )
        )
    return entries


def cached_world_entries(cache: dict[str, Any] | None) -> list[dict[str, str]]:
    if not cache:
        return []
    entries: list[dict[str, str]] = []
    for row in cache.get("npcs") or []:
        if isinstance(row, dict) and row.get("name"):
            entries.append(
                _entry(
                    "npc",
                    str(row["name"]),
                    str(row.get("body") or ""),
                    str(row.get("source") or "session"),
                )
            )
    for row in cache.get("locations") or []:
        if isinstance(row, dict) and row.get("name"):
            entries.append(
                _entry(
                    "location",
                    str(row["name"]),
                    str(row.get("body") or ""),
                    str(row.get("source") or "session"),
                )
            )
    return entries


def extract_marked_names(text: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for match in _MARKDOWN_NAME.findall(text or ""):
        name = match.strip()
        key = _norm(name)
        if key in seen or key in _COMMON_FALSE_POSITIVES or len(key) < 2:
            continue
        seen.add(key)
        names.append(name)
    return names


def heuristic_extract(session: dict[str, Any]) -> list[dict[str, str]]:
    """Pull clearly marked names from session messages and lonelog."""
    chunks: list[str] = [str(session.get("lonelog") or "")]
    for msg in session.get("messages") or []:
        chunks.append(str(msg.get("content") or ""))
    blob = "\n".join(chunks)
    return [_entry("npc", name, "", "session") for name in extract_marked_names(blob)]


def _persist_extracted(
    *,
    campaign_id: str,
    updates: JournalTurnUpdates,
    session_entries: list[dict[str, str]],
) -> list[dict[str, str]]:
    added = list(session_entries)
    if campaign_id and get_campaign(campaign_id):
        apply_journal_updates(campaign_id=campaign_id, adventure_id=None, updates=updates)
        return added
    for npc in updates.new_npcs + updates.updated_npcs:
        if npc.name.strip():
            added.append(_entry("npc", npc.name.strip(), npc.body.strip(), "session"))
    for loc in updates.new_locations + updates.updated_locations:
        if loc.name.strip():
            added.append(_entry("location", loc.name.strip(), loc.body.strip(), "session"))
    return added


def _llm_extract(session: dict[str, Any], campaign_id: str) -> list[dict[str, str]]:
    messages = session.get("messages") or []
    if not messages:
        return []
    transcript = []
    for msg in messages[-12:]:
        role = "Player" if msg.get("role") == "user" else "DM"
        transcript.append(f"{role}: {str(msg.get('content') or '')[:800]}")
    user_message = "\n".join(transcript[-4:])
    dm_response = "\n".join(transcript)
    if campaign_id and get_campaign(campaign_id):
        updates = extract_journal_updates(
            campaign_id=campaign_id,
            user_message=user_message,
            dm_response=dm_response,
        )
        _persist_extracted(campaign_id=campaign_id, updates=updates, session_entries=[])
        return []
    # Session-only campaigns still get a journal-shaped extract, persisted locally.
    from langchain_core.messages import HumanMessage

    from backend.games.dnd5e.prompts import dnd5e_stable_system_prompt
    from backend.llm import cached_system, structured_llm

    llm = structured_llm(JournalTurnUpdates)
    updates = llm.invoke(
        [
            cached_system(dnd5e_stable_system_prompt()),
            HumanMessage(
                content=(
                    "Extract named NPCs and locations clearly introduced "
                    "in this solo play transcript. Only include names that "
                    "appear in the text. Prefer empty lists over guesses.\n\n"
                    f"{dm_response[:4000]}"
                )
            ),
        ]
    )
    return _persist_extracted(campaign_id="", updates=updates, session_entries=[])


def _split(entries: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    npcs = [e for e in entries if e.get("kind") == "npc"]
    locations = [e for e in entries if e.get("kind") == "location"]
    return npcs, locations


def _payload(entries: list[dict[str, str]], message_count: int) -> dict[str, Any]:
    npcs, locations = _split(_merge_entries(entries))
    return {
        "npcs": [
            {"name": e["name"], "body": e["body"], "source": e.get("source", "session")}
            for e in npcs
        ],
        "locations": [
            {"name": e["name"], "body": e["body"], "source": e.get("source", "session")}
            for e in locations
        ],
        "message_count": message_count,
    }


def assemble_world_entries(
    session: dict[str, Any],
    *,
    cache: dict[str, Any] | None = None,
    extra: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    campaign_id = _campaign_id_for_session(session)
    rows = campaign_world_entries(campaign_id)
    rows.extend(cached_world_entries(cache))
    if extra:
        rows.extend(extra)
    return _merge_entries(rows)


def get_or_refresh_world(session_id: str, *, refresh: bool = False) -> dict[str, Any]:
    """Return NPCs and locations, extracting from play when the cache is stale."""
    session = get_session(session_id)
    if not session:
        raise ValueError("Session not found")
    count = len(session.get("messages") or [])
    cache = get_session_world_cache(session_id)
    extra: list[dict[str, str]] = []
    stale = cache is None or cache.get("message_count") != count
    if (refresh or stale) and count > 0:
        extra.extend(heuristic_extract(session))
        if refresh:
            try:
                extra.extend(_llm_extract(session, _campaign_id_for_session(session)))
            except Exception:
                pass
    entries = assemble_world_entries(session, cache=cache, extra=extra)
    payload = _payload(entries, count)
    save_session_world_cache(session_id, payload)
    return payload
