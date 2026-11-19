#!/usr/bin/env python3
"""Backup and repair Larry Swordstein if the local/production save is present.

Only writes armor, weapons, and derived AC when those fields are clearly wrong.
Never deletes. Copies character.json to a timestamped backup first.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.games.dnd5e.characters.character_builder import rebuild_character
from backend.games.dnd5e.characters.entity import character_from_dict, character_to_dict
from backend.storage import CHARACTERS_DIR, get_character, list_characters, save_character


def _hydrate_from_gcs() -> None:
    """Pull character saves from gs://celssi-auto-dm when credentials exist."""
    try:
        from backend.gcs_sync import download_prefix

        count = download_prefix("saves/characters/", CHARACTERS_DIR)
        print(f"GCS hydrate: {count} character files.")
    except Exception as exc:
        print(f"GCS hydrate skipped: {exc}")

LARRY_NAMES = {"larry swordstein", "larry"}


def _find_larry() -> str | None:
    for row in list_characters():
        name = str(row.get("name") or "").strip().lower()
        if name in LARRY_NAMES or "swordstein" in name:
            return str(row["id"])
    return None


def _needs_repair(data: dict) -> bool:
    armor = str(data.get("armor") or "none").strip().lower()
    weapons = data.get("weapons") or []
    names = {str(w.get("name") or "").strip().lower() for w in weapons if isinstance(w, dict)}
    if armor in ("", "none") and str(data.get("starting_gear_choice") or "") == "heavy":
        return True
    if "greatsword" not in names and str(data.get("starting_gear_choice") or "") == "heavy":
        return True
    if int(data.get("ac") or 0) < 17 and str(data.get("fighting_style_feat") or "").lower() == "defense":
        return True
    return False


def main() -> int:
    _hydrate_from_gcs()
    char_id = _find_larry()
    if not char_id:
        print("Larry Swordstein not found in this environment. No production write.")
        return 0
    data = get_character(char_id)
    if not data:
        print(f"Character id {char_id} listed but file missing. No write.")
        return 1
    path = CHARACTERS_DIR / char_id / "character.json"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"character.backup-{stamp}.json")
    if path.is_file():
        shutil.copy2(path, backup)
        print(f"Backup: {backup}")
        try:
            from backend.gcs_sync import upload_blob

            rel = backup.resolve().relative_to(CHARACTERS_DIR.parent.resolve()).as_posix()
            upload_blob(f"saves/{rel}", backup)
            print(f"Backup uploaded to gs://celssi-auto-dm/saves/{rel}")
        except Exception as exc:
            print(f"GCS backup upload skipped: {exc}")
    if not _needs_repair(data):
        print(f"{char_id} already looks consistent. No write.")
        return 0
    rebuilt = character_to_dict(rebuild_character(character_from_dict(data)))
    save_character(char_id, rebuilt)
    print(
        json.dumps(
            {
                "id": char_id,
                "armor": rebuilt.get("armor"),
                "ac": rebuilt.get("ac"),
                "weapons": [w.get("name") for w in (rebuilt.get("weapons") or []) if isinstance(w, dict)],
            },
            indent=2,
        )
    )
    print("Wrote rebuilt Larry sheet (no deletes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
