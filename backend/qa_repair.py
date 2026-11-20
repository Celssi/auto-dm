"""One-shot repair for the three QA characters and empty lonelog rows.

Runs on Cloud Run boot after GCS hydrate so production sheets persist 2024
defaults and live combat resources without waiting for a browser load.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

QA_CHARACTER_IDS = ("b819a0ec", "910d9c4c", "c5baf24a")
QA_SESSION_ID = "622d3723"


def _session_ids_for_character(char_id: str) -> list[str]:
    from backend.storage import list_sessions

    ids: list[str] = []
    for session in list_sessions(include_archived=True):
        if session.get("character_id") == char_id and session.get("id"):
            ids.append(str(session["id"]))
    if QA_SESSION_ID not in ids:
        ids.append(QA_SESSION_ID)
    return ids


def _overlay_from_session(char_id: str, data: dict[str, Any]) -> dict[str, Any]:
    from backend.dm.encounters import load_combat_state
    from backend.games.dnd5e.dm.combat_manager import sync_player_combatant
    from backend.games.dnd5e.dm.resource_keeper import overlay_live_resources
    from backend.storage import get_session, get_session_lonelog

    out = dict(data)
    for session_id in _session_ids_for_character(char_id):
        combat = load_combat_state(session_id)
        if combat and combat.status == "active":
            out = sync_player_combatant(combat, out)
        session = get_session(session_id) or {}
        messages = session.get("messages") or []
        for message in reversed(messages):
            if str(message.get("role") or "") != "assistant":
                continue
            overlay = overlay_live_resources(out, str(message.get("content") or ""))
            overlay.pop("_logs", None)
            if overlay:
                out.update(overlay)
            break
        log = get_session_lonelog(session_id)
        if "magic initiate" in log.lower() and "no slot" in log.lower():
            fc = dict(out.get("feature_choices") or {})
            fc["_magic_initiate_free_used"] = True
            if not str(fc.get("magic_initiate_level1") or "").strip():
                fc["magic_initiate_level1"] = "Shield"
            out["feature_choices"] = fc
    return out


def _fingerprint(data: dict[str, Any]) -> dict[str, Any]:
    from backend.games.registry import _migration_fields

    return _migration_fields(data)


def repair_qa_characters() -> dict[str, Any]:
    from backend.dm.lonelog import sanitize_lonelog_content
    from backend.games.registry import rebuild_character_dict_persisting
    from backend.storage import (
        get_character,
        get_session_lonelog,
        list_characters,
        list_sessions,
        save_character,
        write_session_lonelog,
    )

    report: dict[str, Any] = {"characters": {}, "lonelogs": []}
    roster_ids = [str(row.get("id") or "") for row in list_characters() if row.get("id")]
    seen_ids = list(dict.fromkeys([*QA_CHARACTER_IDS, *roster_ids]))
    for char_id in seen_ids:
        data = get_character(char_id)
        if not data:
            if char_id in QA_CHARACTER_IDS:
                report["characters"][char_id] = {"status": "missing"}
            continue
        if data.get("id") != char_id:
            data = {**data, "id": char_id}
        overlaid = _overlay_from_session(char_id, data) if char_id in QA_CHARACTER_IDS else data
        before = _fingerprint(overlaid)
        rebuilt = rebuild_character_dict_persisting(char_id, overlaid)
        after = _fingerprint(rebuilt)
        if char_id in QA_CHARACTER_IDS:
            save_character(char_id, rebuilt)
            report["characters"][char_id] = {
                "status": "repaired",
                "fingerprint": after,
            }
            logger.info("QA repair persisted %s %s", char_id, after)
        elif before != after:
            report["characters"][char_id] = {
                "status": "migrated",
                "fingerprint": after,
            }
            logger.info("Migrated stored choice lists on %s", char_id)

    seen: set[str] = set()
    for session in list_sessions(include_archived=True):
        sid = str(session.get("id") or "")
        if sid:
            seen.add(sid)
    seen.add(QA_SESSION_ID)
    for sid in seen:
        original = get_session_lonelog(sid)
        if not original:
            continue
        cleaned = sanitize_lonelog_content(original)
        if cleaned != original:
            write_session_lonelog(sid, cleaned)
            report["lonelogs"].append(sid)
            logger.info("QA repair sanitized lonelog %s", sid)
    return report
