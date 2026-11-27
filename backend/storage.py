"""File-based persistence for characters, adventures, and sessions."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import SAVES_DIR
from backend.persist import after_delete, after_write

logger = logging.getLogger(__name__)


def _now_iso() -> str:
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
        after_write(path)
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


def _append_text(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")
    after_write(path)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    after_write(path)


def _read_text(path: Path, default: str = "") -> str:
    if not path.is_file():
        return default
    return path.read_text(encoding="utf-8")


CHARACTER_REV_KEY = "_rev"
LIVE_CHARACTER_KEYS = (
    "hp",
    "max_hp",
    "ac",
    "spell_slots",
    "hit_dice_spent",
    "hit_dice_max",
    "concentration",
    "conditions",
    "luck_points_remaining",
    "second_wind_remaining",
    "lay_on_hands_remaining",
    "wild_shape_uses",
    "active_effects",
    "heroic_inspiration",
    "inventory",
    "currency",
    "feature_choices",
    "death_save_successes",
    "death_save_failures",
    "exhaustion",
    "savage_attacker_used_this_turn",
    # Brambletrek live resources (sheet edits must not be overwritten by stale snapshots)
    "health",
    "morale",
    "supplies",
    "journey_day",
    "in_aldwund",
    "legacy_abilities_used",
)
_LONELOG_PREFIX = re.compile(r"^(@|=>)\s+\S+\s+")


def _refresh_saves_file(path: Path) -> None:
    try:
        from backend.gcs_sync import refresh_saves_path

        refresh_saves_path(path)
    except Exception:
        logger.debug("Saves refresh skipped for %s", path)


def _lonelog_body(line: str) -> str:
    text = (line or "").strip()
    return _LONELOG_PREFIX.sub("", text).strip()


def _merge_messages(disk: list, incoming: list) -> list:
    """Never replace a longer history with a stale shorter snapshot."""
    current = list(disk or [])
    nxt = list(incoming or [])
    if not current:
        return nxt
    if not nxt:
        return current
    if nxt == current:
        return nxt
    if len(nxt) >= len(current) and current == nxt[: len(current)]:
        return nxt
    if len(current) >= len(nxt) and nxt == current[: len(nxt)]:
        return current
    logger.warning(
        "Session message fork (disk=%s incoming=%s); keeping the longer transcript",
        len(current),
        len(nxt),
    )
    return current if len(current) >= len(nxt) else nxt


def _next_character_rev(existing: dict | None) -> int:
    return int((existing or {}).get(CHARACTER_REV_KEY) or 0) + 1


# --- Characters ---

CHARACTERS_DIR = SAVES_DIR / "characters"
CHARACTERS_INDEX = CHARACTERS_DIR / "roster.json"


def list_characters() -> list[dict[str, str]]:
    roster = _read_json(CHARACTERS_INDEX, [])
    out: list[dict[str, str]] = []
    for r in roster:
        cid = r.get("id")
        if not cid:
            continue
        game_id = r.get("game_id")
        if not game_id:
            full = get_character(cid)
            game_id = str((full or {}).get("game_id") or "dnd5e")
        out.append(
            {
                "id": cid,
                "name": r.get("name", "Hero"),
                "game_id": game_id or "dnd5e",
            }
        )
    return out


def get_character(char_id: str) -> dict | None:
    path = CHARACTERS_DIR / char_id / "character.json"
    _refresh_saves_file(path)
    return _read_json(path)


def patch_character(char_id: str, updates: dict) -> dict:
    """Merge live fields onto the disk sheet. Never write a stale full snapshot."""
    from backend.session_locks import character_lock

    clean = {k: v for k, v in (updates or {}).items() if not str(k).startswith("_")}
    with character_lock(char_id):
        path = CHARACTERS_DIR / char_id / "character.json"
        _refresh_saves_file(path)
        existing = _read_json(path, {}) or {}
        merged = dict(existing)
        for key, value in clean.items():
            merged[key] = value
        merged["id"] = char_id
        merged[CHARACTER_REV_KEY] = _next_character_rev(existing)
        _write_json(path, merged)
        name = str(merged.get("name") or existing.get("name") or "Hero").strip() or "Hero"
        _touch_character_roster(char_id, name, merged)
        return merged


def save_character(char_id: str | None, data: dict) -> str:
    if not char_id:
        char_id = str(uuid.uuid4())[:8]
    from backend.session_locks import character_lock

    with character_lock(char_id):
        path = CHARACTERS_DIR / char_id / "character.json"
        _refresh_saves_file(path)
        existing = _read_json(path, {}) or {}
        incoming = dict(data or {})
        disk_rev = int(existing.get(CHARACTER_REV_KEY) or 0)
        incoming_rev = incoming.get(CHARACTER_REV_KEY)
        if existing and incoming_rev is not None and int(incoming_rev or 0) < disk_rev:
            logger.warning(
                "Ignoring stale character snapshot %s rev %s < disk %s",
                char_id,
                incoming_rev,
                disk_rev,
            )
            for key in LIVE_CHARACTER_KEYS:
                if key in existing:
                    incoming[key] = existing[key]
        merged = dict(existing)
        merged.update(incoming)
        merged["id"] = char_id
        merged[CHARACTER_REV_KEY] = disk_rev + 1
        name = str(merged.get("name") or "Hero").strip() or "Hero"
        _write_json(path, merged)
        _touch_character_roster(char_id, name, merged)
        return char_id


def _touch_character_roster(char_id: str, name: str, data: dict) -> None:
    roster = _read_json(CHARACTERS_INDEX, [])
    found = False
    for entry in roster:
        if entry.get("id") == char_id:
            entry["name"] = name
            entry["game_id"] = str(data.get("game_id") or entry.get("game_id") or "dnd5e")
            entry["updated_at"] = _now_iso()
            found = True
            break
    if not found:
        roster.append(
            {
                "id": char_id,
                "name": name,
                "game_id": str(data.get("game_id") or "dnd5e"),
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        )
    _write_json(CHARACTERS_INDEX, roster)


def _remove_dir(path: Path) -> None:
    if not path.is_dir():
        return
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()
    after_delete(path)


def list_adventure_ids_for_character(char_id: str) -> list[str]:
    index = _read_json(ADVENTURES_INDEX, [])
    adv_ids: list[str] = []
    for entry in index:
        adv_id = entry.get("id")
        if not adv_id:
            continue
        meta = _read_json(ADVENTURES_DIR / adv_id / "adventure.json", {})
        if meta.get("character_id") == char_id:
            adv_ids.append(adv_id)
    return adv_ids


def delete_sessions_for_adventure(adv_id: str) -> list[str]:
    deleted: list[str] = []
    for session in list_sessions(include_archived=True):
        if session.get("adventure_id") == adv_id and session.get("id"):
            if delete_session(session["id"]):
                deleted.append(session["id"])
    return deleted


def delete_sessions_for_character(char_id: str) -> list[str]:
    deleted: list[str] = []
    for session in list_sessions(include_archived=True):
        if session.get("character_id") == char_id and session.get("id"):
            if delete_session(session["id"]):
                deleted.append(session["id"])
    return deleted


def delete_character(char_id: str) -> bool:
    roster = _read_json(CHARACTERS_INDEX, [])
    if not any(r.get("id") == char_id for r in roster):
        return False

    from backend.journal_storage import remove_character_from_campaigns

    remove_character_from_campaigns(char_id)
    for adv_id in list_adventure_ids_for_character(char_id):
        delete_adventure(adv_id)
    delete_sessions_for_character(char_id)

    new_roster = [r for r in roster if r.get("id") != char_id]
    _write_json(CHARACTERS_INDEX, new_roster)
    _remove_dir(CHARACTERS_DIR / char_id)
    return True


# --- Adventures ---

ADVENTURES_DIR = SAVES_DIR / "adventures"
ADVENTURES_INDEX = ADVENTURES_DIR / "index.json"


def list_adventures(campaign_id: str | None = None) -> list[dict[str, str]]:
    index = _read_json(ADVENTURES_INDEX, [])
    rows = []
    for a in index:
        if not a.get("id"):
            continue
        char_id = a.get("character_id")
        if char_id is None:
            meta = _read_json(ADVENTURES_DIR / a["id"] / "adventure.json", {})
            char_id = str(meta.get("character_id") or "").strip()
        else:
            meta = _read_json(ADVENTURES_DIR / a["id"] / "adventure.json", {})
        rows.append(
            {
                "id": a["id"],
                "name": a.get("name", "Adventure"),
                "mode": a.get("mode", "freeform"),
                "status": a.get("status", "draft"),
                "campaign_id": a.get("campaign_id", ""),
                "sequence": a.get("sequence"),
                "source_module": a.get("source_module"),
                "character_id": char_id or "",
                "game_id": str(meta.get("game_id") or a.get("game_id") or "dnd5e"),
            }
        )
    if campaign_id:
        rows = [a for a in rows if a.get("campaign_id") == campaign_id]
    return rows


def list_adventures_for_campaign(campaign_id: str) -> list[dict[str, str]]:
    return list_adventures(campaign_id=campaign_id)


def get_adventure(adv_id: str) -> dict | None:
    if not (ADVENTURES_DIR / adv_id / "adventure.json").is_file():
        # Created on another Cloud Run instance: pull it from the saves bucket first.
        for name in ("adventure.json", "outline.md", "log.md", "summary.md"):
            _refresh_saves_file(ADVENTURES_DIR / adv_id / name)
    meta = _read_json(ADVENTURES_DIR / adv_id / "adventure.json")
    if not meta:
        return None
    meta["outline"] = _read_text(ADVENTURES_DIR / adv_id / "outline.md")
    meta["log"] = _read_text(ADVENTURES_DIR / adv_id / "log.md")
    meta["summary"] = _read_text(ADVENTURES_DIR / adv_id / "summary.md")
    return meta


def get_adventure_summary(adv_id: str) -> str:
    return _read_text(ADVENTURES_DIR / adv_id / "summary.md")


def write_adventure_summary(adv_id: str, content: str) -> None:
    adv_dir = ADVENTURES_DIR / adv_id
    _write_text(adv_dir / "summary.md", content.strip() + "\n")
    meta = _read_json(adv_dir / "adventure.json", {})
    if meta:
        meta["summary_updated_at"] = _now_iso()
        _write_json(adv_dir / "adventure.json", meta)


def save_adventure(adv_id: str | None, meta: dict, outline: str = "", log: str = "") -> str:
    if not adv_id:
        adv_id = str(uuid.uuid4())[:8]
    name = str(meta.get("name") or "Adventure").strip() or "Adventure"
    meta["id"] = adv_id
    meta.setdefault("mode", "freeform")
    meta.setdefault("status", "active")
    meta["updated_at"] = _now_iso()
    if "created_at" not in meta:
        meta["created_at"] = _now_iso()
    adv_dir = ADVENTURES_DIR / adv_id
    _write_json(
        adv_dir / "adventure.json",
        {k: v for k, v in meta.items() if k not in ("outline", "log", "summary")},
    )
    if outline:
        _write_text(adv_dir / "outline.md", outline)
    if log:
        _write_text(adv_dir / "log.md", log)
    index = _read_json(ADVENTURES_INDEX, [])
    found = False
    for entry in index:
        if entry.get("id") == adv_id:
            entry.update(
                {
                    "name": name,
                    "mode": meta.get("mode"),
                    "status": meta.get("status"),
                    "campaign_id": meta.get("campaign_id", ""),
                    "sequence": meta.get("sequence"),
                    "source_module": meta.get("source_module"),
                    "character_id": meta.get("character_id", ""),
                }
            )
            found = True
            break
    if not found:
        index.append(
            {
                "id": adv_id,
                "name": name,
                "mode": meta.get("mode", "freeform"),
                "status": meta.get("status", "active"),
                "campaign_id": meta.get("campaign_id", ""),
                "sequence": meta.get("sequence"),
                "source_module": meta.get("source_module"),
                "character_id": meta.get("character_id", ""),
            }
        )
    _write_json(ADVENTURES_INDEX, index)
    campaign_id = str(meta.get("campaign_id") or "").strip()
    character_id = str(meta.get("character_id") or "").strip()
    if campaign_id and character_id:
        from backend.journal_storage import link_character_to_campaign

        link_character_to_campaign(campaign_id, character_id)
    return adv_id


def append_adventure_log(adv_id: str, entry: str) -> None:
    path = ADVENTURES_DIR / adv_id / "log.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_text(path, f"\n### {ts}\n{entry.strip()}\n")


def delete_adventure(adv_id: str) -> bool:
    index = _read_json(ADVENTURES_INDEX, [])
    new_index = [a for a in index if a.get("id") != adv_id]
    if len(new_index) == len(index):
        return False
    delete_sessions_for_adventure(adv_id)
    _write_json(ADVENTURES_INDEX, new_index)
    _remove_dir(ADVENTURES_DIR / adv_id)
    return True


# --- Sessions ---

SESSIONS_DIR = SAVES_DIR / "sessions"
SESSIONS_INDEX = SESSIONS_DIR / "index.json"


def _session_archived(row: dict) -> bool:
    return bool(row.get("archived"))


def list_sessions(*, include_archived: bool = False) -> list[dict[str, str]]:
    index = _read_json(SESSIONS_INDEX, [])
    rows = [s for s in index if s.get("id")]
    if include_archived:
        return rows
    return [s for s in rows if not _session_archived(s)]


def find_session_for_adventure(adventure_id: str) -> dict[str, str] | None:
    for session in list_sessions(include_archived=False):
        if session.get("adventure_id") == adventure_id:
            return session
    return None


def get_session(session_id: str) -> dict | None:
    meta_path = SESSIONS_DIR / session_id / "session.json"
    messages_path = SESSIONS_DIR / session_id / "messages.json"
    lonelog_path = SESSIONS_DIR / session_id / "lonelog.md"
    _refresh_saves_file(meta_path)
    _refresh_saves_file(messages_path)
    _refresh_saves_file(lonelog_path)
    meta = _read_json(meta_path)
    if not meta:
        return None
    meta["lonelog"] = _read_text(lonelog_path)
    meta["messages"] = _read_json(messages_path, [])
    return meta


def create_session(
    *,
    character_id: str,
    adventure_id: str,
    name: str = "",
    include_faerun: bool = False,
) -> str:
    session_id = str(uuid.uuid4())[:8]
    meta = {
        "id": session_id,
        "name": name or f"Session {session_id}",
        "character_id": character_id,
        "adventure_id": adventure_id,
        "include_faerun": include_faerun,
        "extras": {},
        "archived": False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    sess_dir = SESSIONS_DIR / session_id
    _write_json(sess_dir / "session.json", meta)
    _write_text(sess_dir / "lonelog.md", "# Lonelog session log\n\n_Lonelog session log_\n")
    _write_json(sess_dir / "messages.json", [])
    index = _read_json(SESSIONS_INDEX, [])
    index.insert(
        0,
        {
            "id": session_id,
            "name": meta["name"],
            "character_id": character_id,
            "adventure_id": adventure_id,
            "created_at": meta["created_at"],
            "archived": False,
        },
    )
    _write_json(SESSIONS_INDEX, index)
    return session_id


def update_session(session_id: str, updates: dict) -> None:
    path = SESSIONS_DIR / session_id / "session.json"
    meta = _read_json(path, {})
    meta.update(updates)
    meta["updated_at"] = _now_iso()
    _write_json(path, meta)


def _update_session_index(session_id: str, updates: dict) -> None:
    index = _read_json(SESSIONS_INDEX, [])
    allowed = {"name", "archived", "character_id", "adventure_id"}
    changed = False
    for entry in index:
        if entry.get("id") != session_id:
            continue
        for key, value in updates.items():
            if key in allowed:
                entry[key] = value
                changed = True
        break
    if changed:
        _write_json(SESSIONS_INDEX, index)


def patch_session(session_id: str, updates: dict) -> dict | None:
    """Rename or archive a session. Additive fields only; never deletes files."""
    path = SESSIONS_DIR / session_id / "session.json"
    meta = _read_json(path)
    if not meta:
        return None
    allowed: dict[str, Any] = {}
    if "name" in updates and updates["name"] is not None:
        name = str(updates["name"]).strip()
        if not name:
            raise ValueError("Session name cannot be empty")
        allowed["name"] = name
    if "archived" in updates and updates["archived"] is not None:
        allowed["archived"] = bool(updates["archived"])
    if not allowed:
        return get_session(session_id)
    update_session(session_id, allowed)
    _update_session_index(session_id, allowed)
    return get_session(session_id)


def update_session_extras(session_id: str, extras: dict) -> None:
    path = SESSIONS_DIR / session_id / "session.json"
    _refresh_saves_file(path)
    meta = _read_json(path, {})
    meta["extras"] = extras
    meta["updated_at"] = _now_iso()
    _write_json(path, meta)


def append_session_log(session_id: str, line: str) -> None:
    path = SESSIONS_DIR / session_id / "lonelog.md"
    _refresh_saves_file(path)
    text = (line or "").rstrip()
    if not text:
        return
    existing = _read_text(path)
    last = existing.splitlines()[-1] if existing.strip() else ""
    if last and _lonelog_body(last) == _lonelog_body(text):
        return
    _append_text(path, text)


def save_session_messages(session_id: str, messages: list[dict]) -> None:
    path = SESSIONS_DIR / session_id / "messages.json"
    _refresh_saves_file(path)
    disk = list(_read_json(path, []) or [])
    merged = _merge_messages(disk, messages)
    _write_json(path, merged)


def persist_user_message(session_id: str, user_message: str) -> None:
    """Write the player's line immediately so a reload during the turn keeps it."""
    text = (user_message or "").strip()
    if not text:
        return
    path = SESSIONS_DIR / session_id / "messages.json"
    _refresh_saves_file(path)
    messages = list(_read_json(path, []) or [])
    if messages and messages[-1].get("role") == "user" and messages[-1].get("content") == text:
        return
    messages.append({"role": "user", "content": text})
    save_session_messages(session_id, messages)


def persist_shown_reply(session_id: str, user_message: str, assistant_text: str) -> None:
    """Persist exactly the reply that streamed. Never replace a shown assistant turn."""
    user = (user_message or "").strip()
    shown = assistant_text or ""
    path = SESSIONS_DIR / session_id / "messages.json"
    _refresh_saves_file(path)
    messages = list(_read_json(path, []) or [])
    if messages and messages[-1].get("role") == "assistant":
        prev_user = messages[-2].get("content") if len(messages) >= 2 else ""
        if prev_user == user and messages[-1].get("content"):
            return
        if prev_user == user:
            messages[-1] = {"role": "assistant", "content": shown}
            save_session_messages(session_id, messages)
            return
    if not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != user:
        if user:
            messages.append({"role": "user", "content": user})
    messages.append({"role": "assistant", "content": shown})
    save_session_messages(session_id, messages)


def get_session_lonelog(session_id: str) -> str:
    from backend.dm.lonelog import sanitize_lonelog_content

    return sanitize_lonelog_content(_read_text(SESSIONS_DIR / session_id / "lonelog.md"))


def write_session_lonelog(session_id: str, content: str) -> None:
    _write_text(SESSIONS_DIR / session_id / "lonelog.md", content)


def append_session_audit(session_id: str, event: dict) -> None:
    import json

    payload = dict(event)
    payload.setdefault("ts", _now_iso())
    path = SESSIONS_DIR / session_id / "audit.jsonl"
    _refresh_saves_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    after_write(path)


def get_session_audit(session_id: str, *, limit: int = 200) -> list[dict]:
    import json

    path = SESSIONS_DIR / session_id / "audit.jsonl"
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[dict] = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def delete_session(session_id: str) -> bool:
    index = _read_json(SESSIONS_INDEX, [])
    new_index = [s for s in index if s.get("id") != session_id]
    if len(new_index) == len(index):
        return False
    _write_json(SESSIONS_INDEX, new_index)
    _remove_dir(SESSIONS_DIR / session_id)
    return True


def get_session_recap_cache(session_id: str) -> dict | None:
    data = _read_json(SESSIONS_DIR / session_id / "recap.json")
    return data if isinstance(data, dict) else None


def save_session_recap_cache(session_id: str, data: dict) -> None:
    payload = dict(data)
    payload["updated_at"] = _now_iso()
    _write_json(SESSIONS_DIR / session_id / "recap.json", payload)


def get_session_world_cache(session_id: str) -> dict | None:
    data = _read_json(SESSIONS_DIR / session_id / "world.json")
    return data if isinstance(data, dict) else None


def save_session_world_cache(session_id: str, data: dict) -> None:
    payload = dict(data)
    payload["updated_at"] = _now_iso()
    _write_json(SESSIONS_DIR / session_id / "world.json", payload)
