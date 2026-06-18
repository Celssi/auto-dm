"""Campaign journal: campaigns, NPCs, and locations (ChatDM-style, no books)."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from backend.config import SAVES_DIR

CAMPAIGNS_DIR = SAVES_DIR / "campaigns"
CAMPAIGNS_INDEX = CAMPAIGNS_DIR / "index.json"


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (name or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return (s[:48] or uuid.uuid4().hex[:8])


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


def list_campaigns() -> list[dict[str, str]]:
    index = _read_json(CAMPAIGNS_INDEX, [])
    return [
        {
            "id": row["id"],
            "name": row.get("name", "Campaign"),
            "status": row.get("status", "active"),
        }
        for row in index
        if row.get("id")
    ]


def get_campaign(campaign_id: str) -> dict | None:
    data = _read_json(_campaign_dir(campaign_id) / "campaign.json")
    if not data:
        return None
    data["npcs"] = list_campaign_npcs(campaign_id)
    data["locations"] = list_campaign_locations(campaign_id)
    return data


def save_campaign(campaign_id: str | None, data: dict) -> str:
    if not campaign_id:
        campaign_id = _unique_id(str(data.get("name") or "campaign"), {r["id"] for r in _read_json(CAMPAIGNS_INDEX, [])})
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
    if "created_at" not in data:
        payload["created_at"] = _now_iso()
    else:
        payload["created_at"] = data["created_at"]
    _write_json(_campaign_dir(campaign_id) / "campaign.json", payload)
    index = _read_json(CAMPAIGNS_INDEX, [])
    found = False
    for row in index:
        if row.get("id") == campaign_id:
            row.update({"name": name, "status": payload["status"]})
            found = True
            break
    if not found:
        index.append({"id": campaign_id, "name": name, "status": payload["status"]})
    _write_json(CAMPAIGNS_INDEX, index)
    return campaign_id


def delete_campaign(campaign_id: str) -> bool:
    index = _read_json(CAMPAIGNS_INDEX, [])
    new_index = [r for r in index if r.get("id") != campaign_id]
    if len(new_index) == len(index):
        return False
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
    existing = {p.stem for p in _npcs_dir(campaign_id).glob("*.json")} if _npcs_dir(campaign_id).is_dir() else set()
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
