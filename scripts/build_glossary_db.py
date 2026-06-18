#!/usr/bin/env python3
"""Build dnd5e_glossary.yaml from PHB OCR cache (spells, skills, feats)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.config import CURATED_DIR, DATA_DIR  # noqa: E402
from backend.characters.spell_resources import normalize_spell_name  # noqa: E402

OCR_PLAYER = DATA_DIR / "ocr_cache" / "player.json"
OUT_PATH = CURATED_DIR / "dnd5e_glossary.yaml"

SKILL_IDS = [
    "acrobatics",
    "animal_handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight_of_hand",
    "stealth",
    "survival",
]

SKIP_FEAT_HEADERS = {
    "HIS CHAPTER OFFERS A COLLECTION OF FEAT LIST",
    "FEAT LIST",
    "ORIGIN FEATS",
    "GENERAL FEATS",
}


def _load_ocr_pages() -> list[dict[str, Any]]:
    if not OCR_PLAYER.exists():
        raise SystemExit(f"Missing OCR cache: {OCR_PLAYER}. Run rules ingest first.")
    data = json.loads(OCR_PLAYER.read_text(encoding="utf-8"))
    return list(data.get("pages") or [])


def _pages_text(pages: list[dict[str, Any]], lo: int, hi: int) -> str:
    return "\n\n".join(p["text"] for p in pages if lo <= int(p.get("page") or 0) <= hi)


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = text.replace("1ld6", "1d6").replace("2ld6", "2d6")
    text = re.sub(r"\bina\b", "in a", text)
    text = re.sub(r"\bona\b", "on a", text)
    return text


def _parse_casting_block(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in ("Casting Time", "Range", "Components", "Duration"):
        m = re.search(rf"{re.escape(key)}:\s*(.+?)(?:\n|$)", body)
        if m:
            fields[key.lower().replace(" ", "_")] = _clean(m.group(1))
    return fields


def _parse_level(school_line: str) -> int | None:
    if "cantrip" in school_line.lower():
        return 0
    m = re.search(r"Level\s+(\d+)", school_line, re.I)
    return int(m.group(1)) if m else None


def _parse_school(school_line: str) -> str:
    m = re.search(
        r"(?:Level \d+ |(?:\d+(?:st|nd|rd|th)-level )?)?([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*(?:Cantrip|\(|$)",
        school_line,
    )
    return m.group(1).strip() if m else ""


def extract_spells(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    section = _pages_text(pages, 239, 543)
    start = section.find("SPELL DESCRIPTIONS")
    end = section.find("APPENDIX A")
    if start < 0:
        return {}
    section = section[start : end if end > start else len(section)]

    header_re = re.compile(
        r"\n([A-Z][A-Z0-9'/,\-\(\) ]{2,})\n"
        r"((?:Level \d+ [A-Za-z]+(?:\s+[A-Za-z]+)?|(?:\d+(?:st|nd|rd|th)-level )?[A-Za-z]+ Cantrip)[^\n]*)\n"
        r"\nCasting Time:",
        re.MULTILINE,
    )
    matches = list(header_re.finditer(section))
    spells: dict[str, dict[str, Any]] = {}

    for i, m in enumerate(matches):
        title = _clean(m.group(1).title())
        school_line = m.group(2).strip()
        body_start = m.end() - len("Casting Time:")
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        body = section[body_start:body_end]
        casting = _parse_casting_block(body)
        # Description starts after Duration line
        desc = body
        dm = re.search(r"Duration:\s*.+?\n\n", body, re.DOTALL)
        if dm:
            desc = body[dm.end() :]
        desc = _clean(desc)
        # Trim appendix noise
        desc = re.split(r"\nAPPENDIX|\nINDEX\b", desc)[0].strip()
        desc = _clean(desc)

        key = normalize_spell_name(title)
        if not key or not desc:
            continue
        spells[key] = {
            "title": title,
            "level": _parse_level(school_line),
            "school": _parse_school(school_line),
            "classes": re.sub(r"\s+", " ", school_line[school_line.find("(") + 1 : school_line.rfind(")")]).strip()
            if "(" in school_line
            else "",
            **casting,
            "text": desc,
        }
    return spells


def extract_skills(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    section = _pages_text(pages, 14, 18)
    idx = section.find("SKILLS")
    if idx < 0:
        return {}
    block = section[idx:]
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]

    desc_lines: list[str] = []
    for ln in lines[1:]:
        if ln.startswith("Skill Ability") or ln == "Acrobatics Dexterity":
            break
        if re.match(r"^[A-Z][a-z].*", ln) and "Dexterity" not in ln and "Example Uses" not in ln:
            desc_lines.append(ln)

    # Survival example use appears after the skills table in PHB layout
    survival_m = re.search(
        r"Survival Wisdom\s*\n\s*(Follow tracks[^\n]+(?:\n[^\n]+)?)",
        block,
        re.MULTILINE,
    )
    if survival_m:
        desc_lines.append(_clean(survival_m.group(1)))

    ab_map = {
        "acrobatics": "dex", "animal_handling": "wis", "arcana": "int", "athletics": "str",
        "deception": "cha", "history": "int", "insight": "wis", "intimidation": "cha",
        "investigation": "int", "medicine": "wis", "nature": "int", "perception": "wis",
        "performance": "cha", "persuasion": "cha", "religion": "int",
        "sleight_of_hand": "dex", "stealth": "dex", "survival": "wis",
    }
    skills: dict[str, dict[str, Any]] = {}
    for sid, desc in zip(SKILL_IDS, desc_lines, strict=False):
        label = sid.replace("_", " ").title()
        skills[sid] = {
            "title": label,
            "ability": ab_map[sid],
            "text": _clean(desc),
        }
    return skills


def extract_features(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Class and subclass features from PHB chapter 3 (LEVEL N: NAME blocks)."""
    section = _pages_text(pages, 49, 172)
    feature_re = re.compile(
        r"LEVEL\s+(\d+):\s*([^\n]+)\n+(.*?)(?=LEVEL\s+\d+:\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    features: dict[str, dict[str, Any]] = {}
    for m in feature_re.finditer(section):
        level = int(m.group(1))
        title = _clean(m.group(2))
        text = _clean(m.group(3))
        if len(text) < 30 or len(title) > 80:
            continue
        if re.search(r"^[0-9\s+\-|]+$", title):
            continue
        key = normalize_spell_name(title)
        if not key:
            continue
        features[key] = {"title": title, "level": level, "text": text}
    return features


def extract_feats(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    section = _pages_text(pages, 199, 215)
    feat_re = re.compile(
        r"\n([A-Z][A-Z0-9'/,\-\(\) ]{2,})\n([^\n]*Feat[^\n]*)\n",
        re.MULTILINE,
    )
    matches = [m for m in feat_re.finditer(section) if m.group(1) not in SKIP_FEAT_HEADERS]
    feats: dict[str, dict[str, Any]] = {}

    for i, m in enumerate(matches):
        title = _clean(m.group(1).title())
        category = _clean(m.group(2))
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        text = _clean(section[body_start:body_end])
        key = normalize_spell_name(title)
        if not key or len(text) < 20:
            continue
        feats[key] = {"title": title, "category": category, "text": text}
    return feats


def main() -> None:
    pages = _load_ocr_pages()
    payload = {
        "source": "player.pdf OCR",
        "spells": extract_spells(pages),
        "skills": extract_skills(pages),
        "feats": extract_feats(pages),
        "features": extract_features(pages),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# D&D 5e (2024 PHB) glossary for UI tooltips.\n"
        "# Regenerate: python -m scripts.build_glossary_db\n\n"
    )
    OUT_PATH.write_text(
        header + yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT_PATH.name}: "
        f"{len(payload['spells'])} spells, "
        f"{len(payload['skills'])} skills, "
        f"{len(payload['feats'])} feats, "
        f"{len(payload['features'])} features",
    )


if __name__ == "__main__":
    main()
