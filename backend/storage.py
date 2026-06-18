"""File-based persistence for characters, adventures, and sessions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import SAVES_DIR


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _append_text(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_text(path: Path, default: str = "") -> str:
    if not path.is_file():
        return default
    return path.read_text(encoding="utf-8")


# --- Characters ---

CHARACTERS_DIR = SAVES_DIR / "characters"
CHARACTERS_INDEX = CHARACTERS_DIR / "roster.json"


def list_characters() -> list[dict[str, str]]:
    roster = _read_json(CHARACTERS_INDEX, [])
    return [{"id": r["id"], "name": r.get("name", "Hero")} for r in roster if r.get("id")]


def get_character(char_id: str) -> dict | None:
    path = CHARACTERS_DIR / char_id / "character.json"
    return _read_json(path)


def save_character(char_id: str | None, data: dict) -> str:
    if not char_id:
        char_id = str(uuid.uuid4())[:8]
    name = str(data.get("name") or "Hero").strip() or "Hero"
    data["id"] = char_id
    _write_json(CHARACTERS_DIR / char_id / "character.json", data)
    roster = _read_json(CHARACTERS_INDEX, [])
    found = False
    for entry in roster:
        if entry.get("id") == char_id:
            entry["name"] = name
            entry["updated_at"] = _now_iso()
            found = True
            break
    if not found:
        roster.append({"id": char_id, "name": name, "created_at": _now_iso(), "updated_at": _now_iso()})
    _write_json(CHARACTERS_INDEX, roster)
    return char_id


def delete_character(char_id: str) -> bool:
    roster = _read_json(CHARACTERS_INDEX, [])
    new_roster = [r for r in roster if r.get("id") != char_id]
    if len(new_roster) == len(roster):
        return False
    _write_json(CHARACTERS_INDEX, new_roster)
    char_dir = CHARACTERS_DIR / char_id
    if char_dir.exists():
        for f in char_dir.iterdir():
            f.unlink()
        char_dir.rmdir()
    return True


# --- Adventures ---

ADVENTURES_DIR = SAVES_DIR / "adventures"
ADVENTURES_INDEX = ADVENTURES_DIR / "index.json"


def list_adventures() -> list[dict[str, str]]:
    index = _read_json(ADVENTURES_INDEX, [])
    return [
        {
            "id": a["id"],
            "name": a.get("name", "Adventure"),
            "mode": a.get("mode", "freeform"),
            "status": a.get("status", "draft"),
            "campaign_id": a.get("campaign_id", ""),
        }
        for a in index
        if a.get("id")
    ]


def get_adventure(adv_id: str) -> dict | None:
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
    _write_json(adv_dir / "adventure.json", {k: v for k, v in meta.items() if k not in ("outline", "log", "summary")})
    if outline:
        _write_text(adv_dir / "outline.md", outline)
    if log:
        _write_text(adv_dir / "log.md", log)
    index = _read_json(ADVENTURES_INDEX, [])
    found = False
    for entry in index:
        if entry.get("id") == adv_id:
            entry.update({
                "name": name,
                "mode": meta.get("mode"),
                "status": meta.get("status"),
                "campaign_id": meta.get("campaign_id", ""),
            })
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
            }
        )
    _write_json(ADVENTURES_INDEX, index)
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
    _write_json(ADVENTURES_INDEX, new_index)
    adv_dir = ADVENTURES_DIR / adv_id
    if adv_dir.exists():
        for f in adv_dir.iterdir():
            f.unlink()
        adv_dir.rmdir()
    return True


# --- Sessions ---

SESSIONS_DIR = SAVES_DIR / "sessions"
SESSIONS_INDEX = SESSIONS_DIR / "index.json"


def list_sessions() -> list[dict[str, str]]:
    index = _read_json(SESSIONS_INDEX, [])
    return [s for s in index if s.get("id")]


def get_session(session_id: str) -> dict | None:
    meta = _read_json(SESSIONS_DIR / session_id / "session.json")
    if not meta:
        return None
    meta["lonelog"] = _read_text(SESSIONS_DIR / session_id / "lonelog.md")
    meta["messages"] = _read_json(SESSIONS_DIR / session_id / "messages.json", [])
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
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    sess_dir = SESSIONS_DIR / session_id
    _write_json(sess_dir / "session.json", meta)
    _write_text(sess_dir / "lonelog.md", "# Lonelog session log\n\n_Lonelog session log_\n")
    _write_json(sess_dir / "messages.json", [])
    index = _read_json(SESSIONS_INDEX, [])
    index.insert(0, {
        "id": session_id,
        "name": meta["name"],
        "character_id": character_id,
        "adventure_id": adventure_id,
        "created_at": meta["created_at"],
    })
    _write_json(SESSIONS_INDEX, index)
    return session_id


def update_session(session_id: str, updates: dict) -> None:
    path = SESSIONS_DIR / session_id / "session.json"
    meta = _read_json(path, {})
    meta.update(updates)
    meta["updated_at"] = _now_iso()
    _write_json(path, meta)


def append_session_log(session_id: str, line: str) -> None:
    _append_text(SESSIONS_DIR / session_id / "lonelog.md", line)


def save_session_messages(session_id: str, messages: list[dict]) -> None:
    _write_json(SESSIONS_DIR / session_id / "messages.json", messages)


def get_session_lonelog(session_id: str) -> str:
    return _read_text(SESSIONS_DIR / session_id / "lonelog.md")


def write_session_lonelog(session_id: str, content: str) -> None:
    _write_text(SESSIONS_DIR / session_id / "lonelog.md", content)


def delete_session(session_id: str) -> bool:
    index = _read_json(SESSIONS_INDEX, [])
    new_index = [s for s in index if s.get("id") != session_id]
    if len(new_index) == len(index):
        return False
    _write_json(SESSIONS_INDEX, new_index)
    sess_dir = SESSIONS_DIR / session_id
    if sess_dir.exists():
        for f in sess_dir.iterdir():
            f.unlink()
        sess_dir.rmdir()
    return True
