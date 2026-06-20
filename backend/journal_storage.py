"""Campaign journal: campaigns, NPCs, and locations (ChatDM-style, no books)."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from backend.config import SAVES_DIR

logger = logging.getLogger(__name__)

CAMPAIGNS_DIR = SAVES_DIR / "campaigns"
CAMPAIGNS_INDEX = CAMPAIGNS_DIR / "index.json"


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Corrupt JSON file, returning default: %s", path)
        return default


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (name or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:48] or uuid.uuid4().hex[:8]


def _unique_id(base: str, existing: set[str]) -> str:
    candidate = slugify(base)
    if candidate not in existing:
        return candidate
    for i in range(2, 100):
        alt = f"{candidate}-{i}"
        if alt not in existing:
            return alt
    return uuid.uuid4().hex[:8]


def _campaign_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / campaign_id


def _npcs_dir(campaign_id: str) -> Path:
    return _campaign_dir(campaign_id) / "npcs"


def _locations_dir(campaign_id: str) -> Path:
    return _campaign_dir(campaign_id) / "locations"


# --- Campaigns ---


def _character_ids_from_adventures(campaign_id: str) -> list[str]:
    from backend.storage import ADVENTURES_DIR, list_adventures_for_campaign

    ids: list[str] = []
    seen: set[str] = set()
    for adv in list_adventures_for_campaign(campaign_id):
        meta = _read_json(ADVENTURES_DIR / adv["id"] / "adventure.json", {})
        char_id = str(meta.get("character_id") or "").strip()
        if char_id and char_id not in seen:
            seen.add(char_id)
            ids.append(char_id)
    return ids


def resolve_campaign_character_ids(
    campaign_id: str,
    stored: list[str] | None = None,
    *,
    persist: bool = False,
) -> list[str]:
    """Return linked character ids, inferring from adventures when the campaign has none."""
    if stored is None:
        data = _read_json(_campaign_dir(campaign_id) / "campaign.json")
        stored = list(data.get("character_ids") or []) if data else []
    merged = list(stored)
    for char_id in _character_ids_from_adventures(campaign_id):
        if char_id not in merged:
            merged.append(char_id)
    if persist and merged != stored:
        data = _read_json(_campaign_dir(campaign_id) / "campaign.json")
        if data:
            save_campaign(campaign_id, {**data, "character_ids": merged})
    return merged


def link_character_to_campaign(campaign_id: str, character_id: str) -> None:
    char_id = (character_id or "").strip()
    if not campaign_id or not char_id:
        return
    data = _read_json(_campaign_dir(campaign_id) / "campaign.json")
    if not data:
        return
    ids = list(data.get("character_ids") or [])
    if char_id in ids:
        return
    save_campaign(campaign_id, {**data, "character_ids": ids + [char_id]})


def list_campaigns() -> list[dict[str, Any]]:
    index = _read_json(CAMPAIGNS_INDEX, [])
    result: list[dict[str, Any]] = []
    for row in index:
        cid = row.get("id")
        if not cid:
            continue
        char_ids = row.get("character_ids")
        if char_ids is None:
            data = _read_json(_campaign_dir(cid) / "campaign.json")
            char_ids = list(data.get("character_ids") or []) if data else []
        char_ids = resolve_campaign_character_ids(cid, char_ids, persist=True)
        result.append(
            {
                "id": cid,
                "name": row.get("name", "Campaign"),
                "status": row.get("status", "active"),
                "character_ids": char_ids,
            }
        )
    return result


def get_campaign(campaign_id: str) -> dict | None:
    data = _read_json(_campaign_dir(campaign_id) / "campaign.json")
    if not data:
        return None
    data["character_ids"] = resolve_campaign_character_ids(
        campaign_id,
        list(data.get("character_ids") or []),
        persist=True,
    )
    data["npcs"] = list_campaign_npcs(campaign_id)
    data["locations"] = list_campaign_locations(campaign_id)
    return data


def save_campaign(campaign_id: str | None, data: dict) -> str:
    if not campaign_id:
        campaign_id = _unique_id(
            str(data.get("name") or "campaign"), {r["id"] for r in _read_json(CAMPAIGNS_INDEX, [])}
        )
    else:
        existing_ids = {r["id"] for r in _read_json(CAMPAIGNS_INDEX, [])}
        if campaign_id not in existing_ids:
            campaign_id = _unique_id(campaign_id, existing_ids)
    name = str(data.get("name") or "Campaign").strip() or "Campaign"
    payload = {
        "id": campaign_id,
        "name": name,
        "story_arc": str(data.get("story_arc") or "").strip(),
        "status": str(data.get("status") or "active").strip(),
        "character_ids": list(data.get("character_ids") or []),
        "updated_at": _now_iso(),
    }
    for key in ("generation_mode", "source_module", "theme", "adventure_count", "copied_from"):
        if key in data and data[key] not in (None, "", {}):
            payload[key] = data[key]
    if "created_at" not in data:
        payload["created_at"] = _now_iso()
    else:
        payload["created_at"] = data["created_at"]
    _write_json(_campaign_dir(campaign_id) / "campaign.json", payload)
    index = _read_json(CAMPAIGNS_INDEX, [])
    found = False
    for row in index:
        if row.get("id") == campaign_id:
            row.update(
                {
                    "name": name,
                    "status": payload["status"],
                    "character_ids": payload["character_ids"],
                }
            )
            found = True
            break
    if not found:
        index.append(
            {
                "id": campaign_id,
                "name": name,
                "status": payload["status"],
                "character_ids": payload["character_ids"],
            }
        )
    _write_json(CAMPAIGNS_INDEX, index)
    return campaign_id


def remove_character_from_campaigns(char_id: str) -> int:
    updated = 0
    for row in _read_json(CAMPAIGNS_INDEX, []):
        campaign_id = row.get("id")
        if not campaign_id:
            continue
        path = _campaign_dir(campaign_id) / "campaign.json"
        data = _read_json(path)
        if not data:
            continue
        ids = list(data.get("character_ids") or [])
        if char_id not in ids:
            continue
        data["character_ids"] = [cid for cid in ids if cid != char_id]
        data["updated_at"] = _now_iso()
        _write_json(path, data)
        updated += 1
    return updated


def delete_campaign(campaign_id: str) -> bool:
    index = _read_json(CAMPAIGNS_INDEX, [])
    new_index = [r for r in index if r.get("id") != campaign_id]
    if len(new_index) == len(index):
        return False

    from backend.storage import delete_adventure, list_adventures_for_campaign

    for adv in list_adventures_for_campaign(campaign_id):
        adv_id = adv.get("id")
        if adv_id:
            delete_adventure(adv_id)

    _write_json(CAMPAIGNS_INDEX, new_index)
    camp_dir = _campaign_dir(campaign_id)
    if camp_dir.is_dir():
        for path in sorted(camp_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        camp_dir.rmdir()
    return True


def append_story_arc_note(campaign_id: str, note: str) -> None:
    path = _campaign_dir(campaign_id) / "campaign.json"
    data = _read_json(path)
    if not data:
        return
    note = note.strip()
    if not note:
        return
    arc = str(data.get("story_arc") or "").strip()
    data["story_arc"] = f"{arc}\n\n[Plot update]\n{note}".strip() if arc else note
    data["updated_at"] = _now_iso()
    _write_json(path, data)


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def find_journal_entry_id(campaign_id: str, kind: str, name: str) -> str | None:
    """Find NPC or location id by display name (case-insensitive)."""
    target = _normalize_name(name)
    if not target:
        return None
    folder = _npcs_dir(campaign_id) if kind == "npcs" else _locations_dir(campaign_id)
    if not folder.is_dir():
        return None
    for path in folder.glob("*.json"):
        data = _read_json(path, {})
        if _normalize_name(str(data.get("name", ""))) == target:
            return data.get("id") or path.stem
    return None


# --- NPCs ---


def list_campaign_npcs(campaign_id: str) -> list[dict[str, str]]:
    npc_dir = _npcs_dir(campaign_id)
    if not npc_dir.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(npc_dir.glob("*.json")):
        data = _read_json(path, {})
        if data.get("id"):
            rows.append({"id": data["id"], "name": data.get("name", data["id"])})
    return rows


def get_campaign_npc(campaign_id: str, npc_id: str) -> dict | None:
    return _read_json(_npcs_dir(campaign_id) / f"{npc_id}.json")


def save_campaign_npc(campaign_id: str, npc_id: str | None, data: dict) -> str:
    existing = (
        {p.stem for p in _npcs_dir(campaign_id).glob("*.json")}
        if _npcs_dir(campaign_id).is_dir()
        else set()
    )
    if not npc_id:
        npc_id = _unique_id(str(data.get("name") or "npc"), existing)
    name = str(data.get("name") or npc_id).strip() or npc_id
    payload = {
        "id": npc_id,
        "campaign_id": campaign_id,
        "name": name,
        "body": str(data.get("body") or "").strip(),
        "updated_at": _now_iso(),
    }
    if data.get("created_at"):
        payload["created_at"] = data["created_at"]
    else:
        payload["created_at"] = _now_iso()
    _write_json(_npcs_dir(campaign_id) / f"{npc_id}.json", payload)
    return npc_id


def delete_campaign_npc(campaign_id: str, npc_id: str) -> bool:
    path = _npcs_dir(campaign_id) / f"{npc_id}.json"
    if not path.is_file():
        return False
    path.unlink()
    return True


# --- Locations ---


def list_campaign_locations(campaign_id: str) -> list[dict[str, str]]:
    loc_dir = _locations_dir(campaign_id)
    if not loc_dir.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(loc_dir.glob("*.json")):
        data = _read_json(path, {})
        if data.get("id"):
            rows.append({"id": data["id"], "name": data.get("name", data["id"])})
    return rows


def get_campaign_location(campaign_id: str, location_id: str) -> dict | None:
    return _read_json(_locations_dir(campaign_id) / f"{location_id}.json")


def save_campaign_location(campaign_id: str, location_id: str | None, data: dict) -> str:
    existing = (
        {p.stem for p in _locations_dir(campaign_id).glob("*.json")}
        if _locations_dir(campaign_id).is_dir()
        else set()
    )
    if not location_id:
        location_id = _unique_id(str(data.get("name") or "location"), existing)
    name = str(data.get("name") or location_id).strip() or location_id
    payload = {
        "id": location_id,
        "campaign_id": campaign_id,
        "name": name,
        "body": str(data.get("body") or "").strip(),
        "updated_at": _now_iso(),
    }
    if data.get("created_at"):
        payload["created_at"] = data["created_at"]
    else:
        payload["created_at"] = _now_iso()
    _write_json(_locations_dir(campaign_id) / f"{location_id}.json", payload)
    return location_id


def delete_campaign_location(campaign_id: str, location_id: str) -> bool:
    path = _locations_dir(campaign_id) / f"{location_id}.json"
    if not path.is_file():
        return False
    path.unlink()
    return True


def list_campaign_entities(campaign_id: str) -> list[dict[str, str]]:
    """NPCs and locations with journal bodies for UI tooltips."""
    entities: list[dict[str, str]] = []
    for row in list_campaign_npcs(campaign_id):
        npc = get_campaign_npc(campaign_id, row["id"])
        if npc and npc.get("name"):
            entities.append(
                {
                    "kind": "npc",
                    "name": str(npc["name"]),
                    "body": str(npc.get("body") or "").strip(),
                }
            )
    for row in list_campaign_locations(campaign_id):
        loc = get_campaign_location(campaign_id, row["id"])
        if loc and loc.get("name"):
            entities.append(
                {
                    "kind": "location",
                    "name": str(loc["name"]),
                    "body": str(loc.get("body") or "").strip(),
                }
            )
    return entities
