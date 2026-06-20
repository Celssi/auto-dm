#!/usr/bin/env python3
"""Migrate Leyri + campaign data from ChatDM journal resources into auto-dm saves."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHATDM_RESOURCES = ROOT.parent / "ChatDM" / "celssi-chatdm-resources" / "journal"
sys.path.insert(0, str(ROOT))

from backend.characters.character_builder import rebuild_character
from backend.characters.entity import character_from_dict, character_to_dict
from backend.config import ANTHROPIC_API_KEY
from backend.dm.lonelog import adventure_log_to_lonelog
from backend.dm.story_memory import build_offline_summary, generate_full_summary
from backend.journal_storage import (
    save_campaign,
    save_campaign_location,
    save_campaign_npc,
    slugify,
)
from backend.storage import (
    save_adventure,
    save_character,
    save_session_messages,
    write_adventure_summary,
    write_session_lonelog,
)

CHAR_ID = "leyri"
CAMPAIGN_ID = "leyri-campaign"
ADV_ID = "leyri-campaign"
SESSION_ID = "leyri-play"

ADVENTURE_FILES = [
    "adventures/20251026_160631_leyri_s_first_adventure.md",
    "adventures/20251029_185207_leyri__shadows_beneath.md",
    "adventures/20251116_172840_leyri__the_festival_of_first_snow.md",
]

LOG_SECTION = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)
HEADER_LINE = re.compile(r"^(CAMPAIGN|NPC|LOCATION|CREATED|LAST UPDATED):\s*(.*)$", re.IGNORECASE)


def _read(rel: str) -> str:
    path = CHATDM_RESOURCES / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_chatdm_journal(text: str) -> tuple[str, str]:
    """Return (display_name, body) from ChatDM npc/location file."""
    name = ""
    body_lines: list[str] = []
    for line in text.splitlines():
        m = HEADER_LINE.match(line.strip())
        if m:
            key, val = m.group(1).upper(), m.group(2).strip()
            if key == "NPC" or key == "LOCATION":
                name = val
            continue
        body_lines.append(line)
    body = "\n".join(body_lines).strip()
    if not name and body_lines:
        for line in body_lines:
            if line.strip() and not line.startswith("="):
                name = line.strip().split(" - ")[0].strip()
                break
    return name, body


def _import_journal_entries(kind: str) -> int:
    folder = CHATDM_RESOURCES / kind
    if not folder.is_dir():
        return 0
    count = 0
    for path in sorted(folder.glob("leyri_s_first_campaign_*")):
        text = path.read_text(encoding="utf-8")
        name, body = _parse_chatdm_journal(text)
        if not name:
            name = path.stem.replace("leyri_s_first_campaign_", "").replace("_", " ").title()
        entry_id = slugify(name)
        data = {"name": name, "body": body or text.strip()}
        if kind == "npcs":
            save_campaign_npc(CAMPAIGN_ID, entry_id, data)
        else:
            save_campaign_location(CAMPAIGN_ID, entry_id, data)
        count += 1
        print(f"  {kind[:-1]}: {name} ({entry_id})")
    return count


def _parse_adventure_log(md: str) -> list[tuple[datetime, str, str]]:
    if "## Adventure Log" not in md:
        return []
    log_part = md.split("## Adventure Log", 1)[1]
    entries: list[tuple[datetime, str, str]] = []
    parts = LOG_SECTION.split(log_part)
    i = 1
    while i + 1 < len(parts):
        ts_str = parts[i].strip()
        body = parts[i + 1].strip()
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            ts = datetime.min
        entries.append((ts, ts_str, body))
        i += 2
    return entries


def _combined_log() -> str:
    all_entries: list[tuple[datetime, str, str, str]] = []
    for rel in ADVENTURE_FILES:
        md = _read(rel)
        title = md.splitlines()[0].lstrip("# ").strip() if md else rel
        for ts, ts_str, body in _parse_adventure_log(md):
            all_entries.append((ts, ts_str, body, title))
    all_entries.sort(key=lambda row: row[0])
    lines = ["# Adventure log (migrated from ChatDM)\n"]
    current_title = ""
    for _, ts_str, body, title in all_entries:
        if title != current_title:
            current_title = title
            lines.append(f"\n## {title}\n")
        lines.append(f"\n### {ts_str}\n\n{body}\n")
    return "".join(lines)


def _build_outline() -> str:
    return (
        "# Leyri's First Adventure\n\n"
        "_Playable adventure linked to campaign journal `leyri-campaign`._\n\n"
        "NPCs, locations, and the full campaign arc live in **Campaigns** — "
        "the DM loads them automatically during play.\n"
    )


def _build_character() -> dict:
    raw = _read("characters/leyri_of_the_mountains.txt")
    appearance = ""
    personality = ""
    status = ""
    if "APPEARANCE:" in raw:
        appearance = raw.split("APPEARANCE:", 1)[1].split("PERSONALITY:", 1)[0].strip()
    if "PERSONALITY:" in raw:
        personality = raw.split("PERSONALITY:", 1)[1].split("CURRENT STATUS:", 1)[0].strip()
    if "CURRENT STATUS:" in raw:
        status = raw.split("CURRENT STATUS:", 1)[1].split("RELATIONSHIPS:", 1)[0].strip()

    char = character_from_dict(
        {
            "id": CHAR_ID,
            "name": "Leyri of the Mountains",
            "species": "elf",
            "size": "medium",
            "class_name": "druid",
            "subclass": "Circle of the Moon",
            "background": "hermit",
            "alignment": "",
            "level": 3,
            "hp": 19,
            "max_hp": 19,
            "ac": 16,
            "speed": 35,
            "hit_die": 8,
            "hit_dice_max": 3,
            "hit_dice_spent": 0,
            "ability_scores": {
                "str": 8,
                "dex": 16,
                "con": 13,
                "int": 12,
                "wis": 16,
                "cha": 10,
            },
            "ability_scores_set": True,
            "skill_proficiencies": [
                "perception",
                "survival",
                "medicine",
                "religion",
                "insight",
                "arcana",
                "nature",
            ],
            "save_proficiencies": ["int", "wis"],
            "tool_proficiencies": ["herbalism_kit"],
            "origin_feat": "Healer",
            "languages": ["common", "elvish", "druidic"],
            "cantrips": ["Produce Flame", "Druidcraft", "Elementalism"],
            "prepared_spells": [
                "Entangle",
                "Goodberry",
                "Faerie Fire",
                "Detect Magic",
                "Healing Word",
                "Speak with Animals",
                "Cure Wounds",
                "Moonbeam",
                "Starry Wisp",
            ],
            "spell_slots": {"1": 4, "2": 2},
            "wild_shape_uses": 2,
            "armor": "leather",
            "shield": True,
            "weapons": [
                {"name": "Scimitar", "damage": "1d6", "damage_type": "slashing", "ability": "dex"}
            ],
            "inventory": [
                "Druidic focus (mountain oak staff)",
                "Explorer's Pack",
                "Potion of Healing",
                "Healing herbs",
                "Bandages and salves",
                "Stone Sentinel's Core",
            ],
            "currency": {"gp": 9},
            "equipment_notes": (
                "Wood Elf traits: 35 ft speed, Fey Ancestry, Keen Senses (Insight), Trance.\n"
                "Primal Order: Magician.\n"
                "Wild Shape uses: 2/2. Known forms include "
                "Brown Bear, Dire Wolf, Tiger, Wolf, "
                "Riding Horse, Rat, Spider.\n\n"
                f"Appearance: {appearance}\n\nPersonality: {personality}\n\nStatus: {status}"
            ),
            "campaign_setting": "freeform",
            "campaign_notes": (
                "Pinehaven mountain village campaign"
                " — The Sealed Evil Beneath Thornwatch Tower"
            ),
            "classes": [{"class_name": "druid", "level": 3, "subclass": "Circle of the Moon"}],
        }
    )
    char = rebuild_character(char)
    char.id = CHAR_ID
    char.hp = 19
    char.max_hp = 19
    char.ac = 16
    char.speed = 35
    char.ability_scores = {"str": 8, "dex": 16, "con": 13, "int": 12, "wis": 16, "cha": 10}
    char.spell_slots = {"1": 4, "2": 2}
    return character_to_dict(char)


def _write_session(log: str) -> None:
    from backend.config import SAVES_DIR

    sess_dir = SAVES_DIR / "sessions" / SESSION_ID
    sess_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": SESSION_ID,
        "name": "Leyri — Pinehaven campaign (migrated)",
        "character_id": CHAR_ID,
        "adventure_id": ADV_ID,
        "include_faerun": False,
        "created_at": "2025-10-26T16:06:31+00:00",
        "updated_at": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "migrated_from": "ChatDM/celssi-chatdm-resources",
    }
    (sess_dir / "session.json").write_text(
        __import__("json").dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lonelog_note = (
        "Migrated from ChatDM — generated from adventure log. "
        "Continue from Festival of First Snow (Day 4+)."
    )
    write_session_lonelog(SESSION_ID, adventure_log_to_lonelog(log, note=lonelog_note))
    save_session_messages(SESSION_ID, [])

    index_path = SAVES_DIR / "sessions" / "index.json"
    index = (
        __import__("json").loads(index_path.read_text(encoding="utf-8"))
        if index_path.is_file()
        else []
    )
    if not any(s.get("id") == SESSION_ID for s in index):
        index.insert(
            0,
            {
                "id": SESSION_ID,
                "name": meta["name"],
                "character_id": CHAR_ID,
                "adventure_id": ADV_ID,
                "created_at": meta["created_at"],
            },
        )
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(__import__("json").dumps(index, indent=2), encoding="utf-8")


def main() -> int:
    if not CHATDM_RESOURCES.is_dir():
        print(f"ChatDM resources not found: {CHATDM_RESOURCES}", file=sys.stderr)
        return 1

    char = _build_character()
    save_character(CHAR_ID, char)
    print(f"Character: {CHAR_ID} ({char['name']})")

    story_arc = _read("campaigns/leyri_s_first_campaign_campaign.txt").strip()
    save_campaign(
        CAMPAIGN_ID,
        {
            "name": "Leyri's First Campaign",
            "story_arc": story_arc,
            "status": "active",
            "character_ids": [CHAR_ID],
        },
    )
    print(f"Campaign: {CAMPAIGN_ID}")

    print("Importing journal entries:")
    npc_count = _import_journal_entries("npcs")
    loc_count = _import_journal_entries("locations")
    print(f"  total: {npc_count} NPCs, {loc_count} locations")

    outline = _build_outline()
    log = _combined_log()
    save_adventure(
        ADV_ID,
        {
            "name": "Leyri's First Adventure",
            "mode": "freeform",
            "status": "active",
            "character_id": CHAR_ID,
            "campaign_id": CAMPAIGN_ID,
            "migrated_from": "ChatDM",
        },
        outline=outline,
        log=log,
    )
    print(f"Adventure: {ADV_ID} ({len(log.splitlines())} log lines)")

    npc_hints = "\n".join(
        f"- {path.stem.replace('leyri_s_first_campaign_', '').replace('_', ' ').title()}"
        for path in sorted((CHATDM_RESOURCES / "npcs").glob("leyri_s_first_campaign_*"))
    )
    if ANTHROPIC_API_KEY:
        summary = generate_full_summary(
            log=log, outline=outline, story_arc=story_arc, npc_hints=npc_hints
        )
    else:
        summary = build_offline_summary(log=log, outline=outline, story_arc=story_arc)
    write_adventure_summary(ADV_ID, summary)
    print(f"  summary: {len(summary.splitlines())} lines")

    _write_session(log)
    print(f"Session: {SESSION_ID}")

    print("\nMigration complete. Start with: ./scripts/start-app.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
