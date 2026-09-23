#!/usr/bin/env python3
"""Extract Brambletrek adventure module tables from PDFs into curated YAML."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import CURATED_DIR, pdf_path  # noqa: E402
from backend.games.brambletrek.modules.combat_data import (  # noqa: E402
    dragonkeep_combat_section,
    world_tree_combat_section,
)

OUT_DIR = CURATED_DIR / "brambletrek_modules"

RANK_MAP = {
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "10": "10",
    "jack": "jack",
    "queen": "queen",
    "king": "king",
    "ace": "ace",
}

SUIT_MAP = {
    "hearts": "hearts",
    "diamonds": "diamonds",
    "clubs": "clubs",
    "spades": "spades",
}

_RANK_ONLY_RE = re.compile(
    r"^(?P<rank>2|3|4|5|6|7|8|9|10|"
    r"j\s*a\s*c\s*k|queen|king|a\s*c\s*e|"
    r"jack|ace)$",
    re.IGNORECASE,
)
_RANK_RE = re.compile(
    r"^(?P<rank>2|3|4|5|6|7|8|9|10|j\s*a\s*c\s*k|q\s*u\s*e\s*e\s*n|k\s*i\s*n\s*g|a\s*c\s*e|j|q|k|a)\b",
    re.IGNORECASE,
)
_WATERMARK_RE = re.compile(r"Lauri Mukkala \(Order #\d+\)", re.IGNORECASE)
_OCR_FIXES = (
    (re.compile(r"EXPLORA\s+TION", re.I), "EXPLORATION"),
    (re.compile(r"WHA\s+T", re.I), "WHAT"),
    (re.compile(r"SUR\s+VEY\s+OR", re.I), "SURVEYOR"),
    (re.compile(r"LEGA\s+CY", re.I), "LEGACY"),
    (re.compile(r"SNA\s+CKER", re.I), "SNACKER"),
    (re.compile(r"SP\s+ADES", re.I), "SPADES"),
    (re.compile(r"PR\s+OMPT", re.I), "PROMPT"),
    (re.compile(r"V\s+ALUE", re.I), "VALUE"),
    (re.compile(r"ST\s+AT", re.I), "STAT"),
    (re.compile(r"T\s+ASTING", re.I), "TASTING"),
    (re.compile(r"DRA\s+GONKEEP", re.I), "DRAGONKEEP"),
    (re.compile(r"P\s+ADES", re.I), "PADES"),
    (re.compile(r"FR\s+OZEN", re.I), "FROZEN"),
)
_ITEM_TAG_RE = re.compile(r"\(ITEM[^)]*\)", re.IGNORECASE)
_LORE_TAG_RE = re.compile(r"\(LORE[^)]*\)", re.IGNORECASE)
_COMBAT_TAG_RE = re.compile(r"\(Combat[^)]*\)", re.IGNORECASE)
_STAT_RE = re.compile(
    r"(Health|Morale|Supplies)\s*([+\-−])\s*(\d+)",
    re.IGNORECASE,
)
_PAREN_STAT_RE = re.compile(
    r"\(([+\-−])\s*(\d+)\s*(Health|Morale|Supplies)\)",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"\((LORE|ITEM|DEPTHS|EXIT)\)", re.IGNORECASE)
_ALL_STATS_RE = re.compile(
    r"\(([+\-−])\s*(\d+)\s*All\s*Stats\)",
    re.IGNORECASE,
)
_FACE_ONLY_RANKS = frozenset({"j", "q", "k", "a"})
_STAT_TAIL_RE = re.compile(
    r"\((?:[+\-−]\d+\s*(?:Health|Morale|Supplies|All Stats)"
    r"(?:,\s*[+\-−]\d+\s*(?:Health|Morale|Supplies))*"
    r"|\s*ITEM|\s*LORE|\s*DEPTHS|\s*EXIT|\s*Combat)[^)]*\)",
    re.IGNORECASE,
)
_INLINE_RANK_RE = re.compile(
    r"^(?P<rank>j\s*a\s*c\s*k|queen|king|a\s*c\s*e|jack|ace)\s+(?P<body>.+)$",
    re.IGNORECASE,
)


def _strip_watermark(text: str) -> str:
    return _WATERMARK_RE.sub("", text).strip()


def _fix_ocr_spacing(text: str) -> str:
    out = text
    for pattern, repl in _OCR_FIXES:
        out = pattern.sub(repl, out)
    return out


def _clean_pdf_text(text: str) -> str:
    return _fix_ocr_spacing(_strip_watermark(text))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u2212", "-")).strip()


def _rank_key(raw: str) -> str | None:
    s = re.sub(r"\s+", "", raw.lower())
    if s in ("jack", "j"):
        return "jack"
    if s in ("queen", "q"):
        return "queen"
    if s in ("king", "k"):
        return "king"
    if s in ("ace", "a"):
        return "ace"
    if s.isdigit():
        return s
    return None


def _label_from_block(block: str, *, fallback_len: int = 120) -> tuple[str, str]:
    """Prefer first sentence from body when title would be truncated."""
    label, body = _first_title_label(block)
    text = _norm(block)
    if len(label) >= 58 and body:
        first = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)[0].strip()
        if first and len(first) > 20:
            label = first[:fallback_len]
    return label, body or text


def _parse_stats(block: str, *, detect_combat: bool = True) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for m in _STAT_RE.finditer(block):
        key = m.group(1).lower()
        sign = -1 if m.group(2) in ("-", "−") else 1
        row[key] = int(m.group(3)) * sign
    for m in _PAREN_STAT_RE.finditer(block):
        key = m.group(3).lower()
        sign = -1 if m.group(1) in ("-", "−") else 1
        row[key] = int(m.group(2)) * sign
    all_stats = _ALL_STATS_RE.search(block)
    if all_stats:
        sign = -1 if all_stats.group(1) in ("-", "−") else 1
        row["all_stats"] = int(all_stats.group(2)) * sign
    if detect_combat and _COMBAT_TAG_RE.search(block):
        row["combat"] = True
    tags = [t.lower() for t in _TAG_RE.findall(block)]
    if _ITEM_TAG_RE.search(block):
        tags.append("item")
    if _LORE_TAG_RE.search(block):
        tags.append("lore")
    if tags:
        row["tags"] = sorted(set(tags))
    return row


def _strip_stats_for_label(block: str) -> str:
    """Remove stat paren groups but keep ITEM/LORE/COMBAT tags in label source."""
    text = block
    for m in _STAT_RE.finditer(block):
        text = text.replace(m.group(0), "")
    for m in _PAREN_STAT_RE.finditer(block):
        text = text.replace(m.group(0), "")
    text = re.sub(r"\(\s*\)", "", text)
    return _norm(text)


def _first_title_label(text: str) -> tuple[str, str]:
    """Split 'Title: body' or use first sentence as label."""
    text = _norm(text)
    if ":" in text[:80]:
        title, rest = text.split(":", 1)
        title = title.strip()
        body = rest.strip()
        label = title if len(title) < 60 else text[:120]
        return label, body or text
    return text[:80], text


def _extract_rank_blocks(text: str) -> list[tuple[str, str]]:
    """Split page text into (rank_key, block) segments."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    blocks: list[tuple[str, str]] = []
    current_rank: str | None = None
    current_parts: list[str] = []
    for ln in lines:
        m = _RANK_RE.match(ln)
        if m:
            raw_rank = re.sub(r"\s+", "", m.group("rank").lower())
            if raw_rank in _FACE_ONLY_RANKS and len(ln) > 2 and ln[1:2] not in (" ", "\t"):
                # single-letter J/Q/K/A only when followed by space (face card row)
                if not re.match(r"^[JQKA]\s", ln, re.I):
                    m = None
        if m:
            if current_rank:
                blocks.append((current_rank, "\n".join(current_parts)))
            current_rank = _rank_key(m.group("rank"))
            rest = ln[m.end() :].strip()
            current_parts = [rest] if rest else []
        elif current_rank:
            current_parts.append(ln)
    if current_rank:
        blocks.append((current_rank, "\n".join(current_parts)))
    return blocks


def _extract_rank_only_line_blocks(text: str) -> list[tuple[str, str]]:
    """Split when rank appears alone on a line (Winter Gift dual-column pages)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    blocks: list[tuple[str, str]] = []
    current_rank: str | None = None
    current_parts: list[str] = []
    for ln in lines:
        rank_match = _RANK_ONLY_RE.match(ln)
        inline_match = None if rank_match else _INLINE_RANK_RE.match(ln)
        if rank_match or inline_match:
            if current_rank:
                blocks.append((current_rank, "\n".join(current_parts)))
            if rank_match:
                current_rank = _rank_key(rank_match.group("rank"))
                current_parts = []
            else:
                assert inline_match is not None
                current_rank = _rank_key(inline_match.group("rank"))
                current_parts = [inline_match.group("body").strip()]
            continue
        if current_rank:
            current_parts.append(ln)
    if current_rank:
        blocks.append((current_rank, "\n".join(current_parts)))
    return blocks


def parse_suit_journey_page(text: str, suit: str) -> dict[str, Any]:
    """Parse a single-suit journey table page (CARD VALUE SUIT STAT CHANGE)."""
    rows: dict[str, Any] = {}
    for rank, block in _extract_rank_blocks(text):
        if rank not in RANK_MAP.values():
            continue
        label, body = _label_from_block(block)
        stats = _parse_stats(block)
        row = {"label": label}
        if body and body != label:
            row["body"] = body
        row.update({k: v for k, v in stats.items() if k not in ("combat", "tags") or v})
        if stats.get("combat"):
            row["combat"] = True
        if stats.get("tags"):
            row["tags"] = stats["tags"]
        rows[rank] = row
    return rows


def parse_reasons_page(text: str) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for rank, block in _extract_rank_blocks(text):
        if rank not in RANK_MAP.values():
            continue
        label, body = _label_from_block(block)
        row = {"title": label.split(":")[0].strip(), "label": label}
        if body:
            row["body"] = body
        rows[rank] = row
    return rows


def parse_rank_table(text: str, *, title_field: str = "label") -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for rank, block in _extract_rank_blocks(text):
        if rank not in RANK_MAP.values():
            continue
        label, body = _label_from_block(block)
        row = {title_field: label}
        if body and body != label:
            row["body"] = body
        stats = _parse_stats(block, detect_combat=False)
        row.update({k: v for k, v in stats.items() if k not in ("combat", "tags") or v})
        if stats.get("tags"):
            row["tags"] = stats["tags"]
        rows[rank] = row
    return rows


def parse_choose_adventure(text: str) -> dict[str, Any]:
    """Pumpkin Party suit-routing table."""
    rows: dict[str, Any] = {}
    for rank, block in _extract_rank_blocks(text):
        continue  # not rank-based
    # suit-based single row per suit in paragraph form
    mapping = {
        "hearts": "pumpkin_hunt",
        "diamonds": "spirit_catching",
        "clubs": "costume_contest",
        "spades": "pie_tasting",
    }
    upper = text.upper()
    for suit, table_id in mapping.items():
        token = suit.upper()
        if token not in upper:
            continue
        # grab line containing suit name
        for ln in text.splitlines():
            if token in ln.upper() and any(
                w in ln.upper() for w in ("HUNT", "SPIRIT", "COSTUME", "PIE", "EVENT")
            ):
                label = _norm(ln)
                rows[suit] = {
                    "label": label,
                    "scene_table": table_id,
                    "body": _norm(block) if (block := ln) else label,
                }
                break
    # Better: fixed structure from PDF
    return {
        "hearts": {
            "label": "Pumpkin Hunt",
            "scene_table": "pumpkin_hunt",
            "body": "Venture into the pumpkin patch. Use the pumpkin hunt table.",
        },
        "diamonds": {
            "label": "Spirit Catching",
            "scene_table": "spirit_catching",
            "body": "Engage with ethereal guests. Use the spirit catching table.",
        },
        "clubs": {
            "label": "Costume Contest",
            "scene_table": "costume_contest",
            "body": "Show off your costume. Use the costume contest table.",
        },
        "spades": {
            "label": "Pie Tasting",
            "scene_table": "pie_tasting",
            "body": "Sample pies from village bakers. Use the pie tasting table.",
        },
    }


def parse_exploration_events(text: str) -> dict[str, Any]:
    """Rank-only exploration (Dragonkeep paths), including J/Q/K/A face rows."""
    rows: dict[str, Any] = {}
    text = _clean_pdf_text(text)
    for rank, block in _extract_rank_blocks(text):
        if rank not in RANK_MAP.values():
            continue
        stats = _parse_stats(block)
        label = _strip_stats_for_label(block)[:220]
        row = {"label": label}
        row.update({k: v for k, v in stats.items() if k != "tags"})
        if stats.get("tags"):
            row["tags"] = stats["tags"]
        rows[rank] = row
    return rows


def parse_path_locations(text: str) -> dict[str, Any]:
    """Numbered path locations with optional suit sub-tables."""
    text = _clean_pdf_text(text)
    rows: dict[str, Any] = {}
    parts = re.split(r"(?=\n\s*\d+\.\s)", "\n" + text)
    for part in parts:
        m = re.match(r"\s*(\d+)\.\s*(.+)", part, re.DOTALL)
        if not m:
            continue
        num = m.group(1)
        body = m.group(2).strip()
        # Split multiple CARD tables within one location (e.g. loc 2 equipment + loc 4 trees)
        sections = re.split(r"(?=CARD\s+WHAT)", body, flags=re.I)
        title_line = sections[0].split("\n")[0]
        title = _norm(title_line.split("—")[0] if "—" in title_line else title_line)
        row: dict[str, Any] = {"title": title, "body": _norm(sections[0])}
        for section in sections[1:]:
            if "CARD" not in section.upper():
                continue
            sub: dict[str, Any] = row.get("suit_outcomes") or {}
            block = "CARD " + section
            for suit in SUIT_MAP:
                sym = {"hearts": "♥", "diamonds": "♦", "clubs": "♣", "spades": "♠"}[suit]
                for ln in block.splitlines():
                    if sym in ln or re.search(rf"\b{suit}\b", ln, re.I):
                        stats = _parse_stats(ln)
                        sub[suit] = {
                            "label": _norm(re.sub(r"^[♥♦♣♠]\s*", "", ln)),
                            **{k: v for k, v in stats.items() if k != "tags"},
                            **({"tags": stats["tags"]} if stats.get("tags") else {}),
                        }
                        break
            if sub:
                row["suit_outcomes"] = sub
                if len(sections) > 2:
                    row["body"] = _norm(sections[0] + "\n" + section.split("CARD")[0])
        rows[num] = row
    return rows


def _split_dual_column_block(block: str) -> tuple[str, str]:
    """Split a rank block into left and right column text."""
    block = block.strip()
    if not block:
        return "", ""
    if "(Combat)" in block:
        parts = re.split(r"(?<=\(Combat\))\s+(?=[A-Z(])", block)
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
    tails = list(_STAT_TAIL_RE.finditer(block))
    if tails:
        first_end = tails[0].end()
        left = block[:first_end].strip()
        right = block[first_end:].strip()
        if right:
            return left, right
    paras = [p.strip() for p in re.split(r"\n\s*\n", block) if p.strip()]
    if len(paras) >= 2:
        return paras[0], paras[1]
    return block, ""


def parse_winter_gift_frozen(text: str, *, negative: bool = False) -> dict[str, Any]:
    """Dual-column frozen forest (Winter Gift PDF).

    Page 3 (positive): col1→hearts, col2→diamonds.
    Page 4 (negative): col1→clubs, col2→spades.
    """
    suit_pair = ("clubs", "spades") if negative else ("hearts", "diamonds")
    journeys: dict[str, Any] = {s: {} for s in suit_pair}
    for rank, block in _extract_rank_only_line_blocks(text):
        if rank not in RANK_MAP.values():
            continue
        left, right = _split_dual_column_block(block)
        for suit, chunk in zip(suit_pair, (left, right)):
            if not chunk.strip():
                continue
            stats = _parse_stats(chunk)
            label = _norm(
                re.sub(
                    r"\([+\-−]\d+\s*(?:Health|Morale|Supplies)[^)]*\)",
                    "",
                    chunk,
                    flags=re.I,
                )
            )
            label = re.sub(r"\(ITEM\)|\(DEPTHS\)|\(Combat\)", "", label, flags=re.I).strip()
            row = {"label": label[:220]}
            row.update({k: v for k, v in stats.items() if k not in ("combat", "tags")})
            if stats.get("tags"):
                row["tags"] = stats["tags"]
            if re.search(r"\bcombat\b", chunk, re.I):
                row["combat"] = True
            journeys[suit][rank] = row
    return journeys


def page_text(reader: PdfReader, printed_page: int) -> str:
    """Complete Edition: printed page N ≈ reader index N-2 (cover offset)."""
    idx = max(0, printed_page - 2)
    if idx >= len(reader.pages):
        return ""
    return _clean_pdf_text(reader.pages[idx].extract_text() or "")


def standalone_page_text(reader: PdfReader, printed_page: int) -> str:
    idx = max(0, printed_page - 1)
    if idx >= len(reader.pages):
        return ""
    return _clean_pdf_text(reader.pages[idx].extract_text() or "")


def build_world_tree(complete: PdfReader) -> dict[str, Any]:
    reasons = parse_reasons_page(page_text(complete, 39))
    journeys = {
        "hearts": parse_suit_journey_page(page_text(complete, 40), "hearts"),
        "diamonds": parse_suit_journey_page(page_text(complete, 41), "diamonds"),
        "spades": parse_suit_journey_page(page_text(complete, 42), "spades"),
        "clubs": parse_suit_journey_page(page_text(complete, 43), "clubs"),
    }
    return {
        "id": "world_tree",
        "label": "Secrets of the World Tree",
        "source": {
            "pdf": "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf",
            "printed_pages": {"reasons": 39, "journeys": [40, 41, 42, 43], "combat": 44},
        },
        "play": {
            "journey_cards_per_day": 3,
            "use_core_depths": False,
            "use_core_combat": False,
            "reason_key": "rank",
        },
        "journey_heading": "**Heimstre (World Tree)** — three exploration events per day",
        "reasons": reasons,
        "journeys": journeys,
        "notes": [
            "Per-card combat opponents on p. 44 — use adventure combat draw.",
            "Collect 13 Lore pieces as suggested end condition.",
        ],
        "combat": world_tree_combat_section(),
    }


def build_first_frost(complete: PdfReader) -> dict[str, Any]:
    journeys = {
        "hearts": parse_suit_journey_page(page_text(complete, 105), "hearts"),
        "diamonds": parse_suit_journey_page(page_text(complete, 106), "diamonds"),
        "spades": parse_suit_journey_page(page_text(complete, 107), "spades"),
        "clubs": parse_suit_journey_page(page_text(complete, 108), "clubs"),
    }
    snacker = parse_rank_table(page_text(complete, 104), title_field="label")
    return {
        "id": "first_frost",
        "label": "The Warmth of the First Frost",
        "source": {
            "pdf": "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf",
            "printed_pages": {"journeys": [105, 106, 107, 108], "snacker_tactics": 104},
        },
        "play": {
            "journey_cards_per_day": 4,
            "use_core_depths": False,
            "use_core_combat": True,
            "reason_key": "band",
            "tactic_table": "snacker_tactics",
            "tactic_legacy": "snacker",
        },
        "journey_heading": "**Frozen Forest** — exploration events",
        "journeys": journeys,
        "scene_tables": {
            "snacker_tactics": snacker,
        },
    }


def build_pumpkin_party(complete: PdfReader) -> dict[str, Any]:
    scene_tables = {
        "festival_role": parse_rank_table(page_text(complete, 87)),
        "party_companion": parse_rank_table(page_text(complete, 88)),
        "choose_adventure": parse_choose_adventure(page_text(complete, 89)),
        "pumpkin_hunt": parse_rank_table(page_text(complete, 90)),
        "spirit_catching": parse_rank_table(page_text(complete, 91)),
        "costume_contest": parse_rank_table(page_text(complete, 92)),
        "pie_tasting": parse_rank_table(page_text(complete, 94)),
    }
    return {
        "id": "pumpkin_party",
        "label": "The Pumpkin Party",
        "source": {
            "pdf": "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf",
            "printed_pages": {
                "scene_tables": [86, 87, 88, 89, 90, 91, 92],
            },
        },
        "play": {
            "journey_cards_per_day": 1,
            "use_core_depths": False,
            "use_core_combat": True,
            "reason_key": "band",
            "default_scene_table": "choose_adventure",
        },
        "journey_heading": "**Pumpkin Party** — choose your activity (up to 3 draws)",
        "scene_tables": scene_tables,
        "notes": [
            "Draw for festival role and companion at start; up to 3 choose-your-adventure draws.",
            "Route each draw through choose_adventure then the linked scene table.",
        ],
    }


def build_birthday_wonders(reader: PdfReader) -> dict[str, Any]:
    journeys = {
        "hearts": parse_suit_journey_page(standalone_page_text(reader, 4), "hearts"),
        "diamonds": parse_suit_journey_page(standalone_page_text(reader, 5), "diamonds"),
        "spades": parse_suit_journey_page(standalone_page_text(reader, 6), "spades"),
        "clubs": parse_suit_journey_page(standalone_page_text(reader, 7), "clubs"),
    }
    skaeven = {}
    p8 = standalone_page_text(reader, 8)
    if p8:
        skaeven = parse_rank_table(p8)
    return {
        "id": "birthday_wonders",
        "label": "A Birthday of Wonders",
        "source": {
            "pdf": "brambletrek/Brambletrek_-_A_Birthday_of_Wonders.pdf",
            "printed_pages": {"journeys": [4, 5, 6, 7], "skaeven_tactics": 8},
        },
        "play": {
            "journey_cards_per_day": 4,
            "use_core_depths": False,
            "use_core_combat": True,
            "reason_key": "band",
            "encounter_table": "skaeven_tactics",
        },
        "journey_heading": "**Birthday journey** — exploration events",
        "journeys": journeys,
        "scene_tables": {"skaeven_tactics": skaeven} if skaeven else {},
    }


def build_winter_gift(reader: PdfReader) -> dict[str, Any]:
    pos = parse_winter_gift_frozen(standalone_page_text(reader, 3), negative=False)
    neg = parse_winter_gift_frozen(standalone_page_text(reader, 4), negative=True)
    journeys = {
        "hearts": pos.get("hearts", {}),
        "diamonds": pos.get("diamonds", {}),
        "clubs": neg.get("clubs", {}),
        "spades": neg.get("spades", {}),
    }
    surveyor = parse_rank_table(standalone_page_text(reader, 2))
    return {
        "id": "winter_gift",
        "label": "Winter Gift",
        "source": {
            "pdf": "brambletrek/Brambletrek_-_Winter_Gift.pdf",
            "printed_pages": {"journeys": [3, 4], "surveyor_tactics": 2},
        },
        "play": {
            "journey_cards_per_day": 4,
            "use_core_depths": False,
            "use_core_combat": True,
            "reason_key": "band",
            "tactic_table": "surveyor_tactics",
            "tactic_legacy": "surveyor",
        },
        "journey_heading": "**Frozen Forest (Winter Gift)** — exploration events",
        "journeys": journeys,
        "scene_tables": {"surveyor_tactics": surveyor} if surveyor else {},
    }


def build_dragonkeep(complete: PdfReader) -> dict[str, Any]:
    path = parse_path_locations(page_text(complete, 60) + "\n" + page_text(complete, 61))
    exploration = {
        "path_of_tempest": parse_exploration_events(page_text(complete, 64)),
        "path_of_pyre": parse_exploration_events(page_text(complete, 66)),
        "path_of_leaf": parse_exploration_events(page_text(complete, 68)),
    }
    return {
        "id": "dragonkeep",
        "label": "Dungeons of Dragonkeep",
        "source": {
            "pdf": "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf",
            "printed_pages": {
                "path": [59, 60, 61],
                "exploration": [64, 66, 68],
                "combat": [65, 67, 69],
                "eolan": [70, 72, 76, 77, 78, 79, 80, 81, 82],
            },
        },
        "play": {
            "journey_cards_per_day": 3,
            "use_core_depths": False,
            "use_core_combat": False,
            "reason_key": "band",
            "default_scene_table": "path_of_tempest",
        },
        "journey_heading": "**Dragonkeep exploration** — three events per path section",
        "path_locations": path,
        "exploration_tables": exploration,
        "combat": dragonkeep_combat_section(),
        "notes": [
            "Path to Dragonkeep uses numbered locations with suit draws.",
            "Gem paths use exploration_tables (rank-only, 3 cards each).",
            "Elemental opponents and Eolan finale use module combat tables.",
        ],
    }


def _dump(data: dict[str, Any], filename: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    return path


def _count_journey_rows(journeys: dict[str, Any]) -> int:
    n = 0
    for suit in journeys.values():
        if isinstance(suit, dict):
            n += len(suit)
    return n


def main() -> None:
    complete = PdfReader(str(pdf_path("brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf")))
    birthday = PdfReader(str(pdf_path("brambletrek/Brambletrek_-_A_Birthday_of_Wonders.pdf")))
    winter = PdfReader(str(pdf_path("brambletrek/Brambletrek_-_Winter_Gift.pdf")))

    modules = {
        "world_tree.yaml": build_world_tree(complete),
        "first_frost.yaml": build_first_frost(complete),
        "pumpkin_party.yaml": build_pumpkin_party(complete),
        "birthday_wonders.yaml": build_birthday_wonders(birthday),
        "winter_gift.yaml": build_winter_gift(winter),
        "dragonkeep.yaml": build_dragonkeep(complete),
    }

    index = {
        "modules": {
            mid.replace(".yaml", ""): {
                "file": fname,
                "label": data.get("label", mid),
            }
            for fname, data in modules.items()
            for mid in [fname]
        }
    }
    _dump(index, "index.yaml")

    for fname, data in modules.items():
        out = _dump(data, fname)
        journeys = data.get("journeys") or {}
        scenes = data.get("scene_tables") or {}
        expl = data.get("exploration_tables") or {}
        print(
            f"Wrote {out.name}: "
            f"journey_rows={_count_journey_rows(journeys)} "
            f"scene_tables={len(scenes)} "
            f"exploration={len(expl)} "
            f"reasons={len(data.get('reasons') or {})}"
        )


if __name__ == "__main__":
    main()
