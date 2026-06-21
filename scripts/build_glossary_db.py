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
from backend.games.dnd5e.characters.character_data import (  # noqa: E402
    get_background,
    list_backgrounds,
    spells_data,
)
from backend.games.dnd5e.characters.features import (  # noqa: E402
    class_features_data,
    subclass_features_data,
)
from backend.games.dnd5e.characters.spell_resources import normalize_spell_name  # noqa: E402

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

_SPELL_SCHOOL_LINE = (
    r"(?:"
    r"Level\s+\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)?"
    r"|Levei\s+\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)?"
    r"|[A-Za-z]+(?:\s+[A-Za-z]+)?\s+Cantrip"
    r")[^\n]*(?:\n[^\n]+)?"
)

_CLASS_GAIN_RE = re.compile(r"As an? (\w+), you gain the following class features", re.IGNORECASE)

_AMBIGUOUS_FEATURES = {
    "channel divinity",
    "evasion",
    "expertise",
    "extra attack",
    "fighting style",
    "spellcasting",
    "unarmored defense",
    "weapon mastery",
}

_FEATURE_GARBAGE_MARKERS = (
    "Subclass feature Ability Score",
    "Ability Score Improvement 4d6",
    "CHAPTER 5 | FEATS",
)

_INLINE_FEAT_RE = re.compile(
    r"(?i)(?<![a-z])([A-Z][A-Za-z' ]{2,40}?)\s+"
    r"(Origin Feat|General Feat(?:\s*\([^)]+\))?)\s+"
    r"(.+?)(?=(?:[A-Z][A-Za-z' ]{2,40})\s+(?:Origin|General) Feat(?:\s|\()|CHAPTER \d+|\Z)",
    re.DOTALL,
)

_LEVEL_FEATURE_RE = re.compile(
    r"LEVEL\s+(?:(\d+)|[|:\[\]I\]]+)\s*:?\s*([^\n]+)\n+(.*?)"
    r"(?=LEVEL\s+(?:\d+|[|:\[\]I\]]+)\s*:?\s|\Z)",
    re.DOTALL | re.IGNORECASE,
)

_FEATURE_TABLE_BLEED = re.compile(
    r"(?:"
    r"Proficiency Level Bonus Class Features|"
    r"(?:BARD|CLERIC|DRUID|FIGHTER|MONK|PALADIN|RANGER|ROGUE|SORCERER|WARLOCK|WIZARD)\s+FEATURES|"
    r"LEVEL\s*[|I:\[\]]+\s*:\s*SPELLCASTING|"
    r"Changing Your Prepared Spells\. Whenever|"
    r"OHAPTER \d+ \| CHAR(?:ACTER|AQTER)"
    r")",
    re.IGNORECASE,
)

_SUBCLASS_SPELLCASTING = re.compile(r"\bas an (Eldritch Knight|Arcane Trickster)\b", re.I)
_CLASS_SPELL_LIST = re.compile(r"\bwith ([A-Za-z]+) spells\b", re.I)

_FULL_CASTERS = frozenset(
    {"bard", "cleric", "druid", "paladin", "ranger", "sorcerer", "warlock", "wizard"}
)

# Table-only features missing PHB OCR prose (curated tooltip stubs).
_KNOWN_FEATURE_STUBS: dict[str, str] = {
    "Arcane Recovery": (
        "You have learned to regain some of your magical energy by studying your spellbook. "
        "Once per day when you finish a Short Rest, you can choose "
        "expended wizard spell slots to recover. "
        "The slots must have a combined level equal to or less than "
        "half your wizard level (rounded up), "
        "and none of the slots can be 6th level or higher."
    ),
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


def _trim_feature_text(text: str) -> str:
    m = _FEATURE_TABLE_BLEED.search(text)
    if m:
        text = text[: m.start()].strip()
    return text


def _looks_like_feature_table(text: str) -> bool:
    if _FEATURE_TABLE_BLEED.search(text):
        return True
    if re.search(r"\b\d+\s+\+\d\b", text) and "Ability Score Improvement" in text:
        return True
    return False


def _is_garbage_feature(title: str, text: str) -> bool:
    if len(text) < 25:
        return True
    if _looks_like_feature_table(text):
        return True
    if any(m in text for m in _FEATURE_GARBAGE_MARKERS):
        return True
    if title.isupper() and len(title.split()) > 6:
        return True
    return False


def _canonical_feature_title(raw: str) -> str:
    compact = re.sub(r"[^A-Za-z]", "", _clean(raw)).upper()
    if "SPELL" in compact and ("CASTING" in compact or "LOASTING" in compact):
        return "Spellcasting"
    title = re.split(r"\s+LEVEL\s+", _clean(raw), maxsplit=1, flags=re.I)[0].strip()
    if title.isupper():
        return title.title()
    return title


def _infer_spellcasting_class_id(text: str) -> str | None:
    if _SUBCLASS_SPELLCASTING.search(text):
        return None
    m = _CLASS_SPELL_LIST.search(text)
    if not m:
        return None
    class_id = m.group(1).lower()
    return class_id if class_id in _FULL_CASTERS else None


def _parse_feature_level(raw: str | None) -> int | None:
    if raw and str(raw).isdigit():
        return int(raw)
    return None


def _class_at_pos(section: str, pos: int) -> str | None:
    last: str | None = None
    for m in _CLASS_GAIN_RE.finditer(section[:pos]):
        last = str(m.group(1)).lower()
    return last


def _curated_feature_names() -> set[str]:
    names: set[str] = set()
    generic = {"subclass feature", "ability score improvement", "epic boon", "—"}
    for levels in (class_features_data().get("classes") or {}).values():
        if not isinstance(levels, dict):
            continue
        for feature_list in levels.values():
            if not isinstance(feature_list, list):
                continue
            for name in feature_list:
                label = str(name).strip()
                if label and label.lower() not in generic:
                    names.add(label)
    for row in (subclass_features_data().get("subclasses") or {}).values():
        if not isinstance(row, dict):
            continue
        for feature_list in (row.get("features") or {}).values():
            if not isinstance(feature_list, list):
                continue
            for name in feature_list:
                label = str(name).strip()
                if label and label.lower() not in generic:
                    names.add(label)
    return names


def _feature_title_patterns(display_name: str) -> list[str]:
    display_name = _normalize_apostrophes(display_name)
    words = re.sub(r"[^a-zA-Z0-9' ]+", " ", display_name).split()
    if not words:
        return []
    exact = re.sub(r"\s+", " ", display_name.upper()).strip()
    joiner = r"[\s\[\]\(\).'\"-]*"
    patterns = [
        re.escape(exact),
        rf"[^\n]{{0,40}}{joiner.join(re.escape(w.upper()) for w in words)}",
    ]
    seen: set[str] = set()
    out: list[str] = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _extract_standalone_feature(section: str, display_name: str) -> dict[str, Any] | None:
    for title_pat in _feature_title_patterns(display_name):
        block_re = re.compile(
            rf"\n{title_pat}\n\n(.+?)"
            rf"(?=\n[\(\[]?[A-Z][A-Z0-9'/,\-\(\) \[\]]{{2,}}\n\n"
            rf"|\nLEVEL\s+\d+:\s|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        m = block_re.search(section)
        if not m:
            continue
        text = _clean(m.group(1))
        text = _trim_feature_text(text)
        if _is_garbage_feature(display_name, text):
            continue
        return {"title": display_name, "text": text}
    return None


def _split_inline_feats(feats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged = dict(feats)
    for row in feats.values():
        text = str(row.get("text") or "")
        for m in _INLINE_FEAT_RE.finditer(text):
            title = _clean(m.group(1).title())
            category = _clean(m.group(2))
            body = _clean(m.group(3))
            if len(body) < 20:
                continue
            key = normalize_spell_name(title)
            if key and key not in merged:
                merged[key] = {"title": title, "category": category, "text": body}
    return merged


def _feat_key(name: str) -> str:
    base = name.split("(")[0].strip()
    return normalize_spell_name(base)


def _ensure_background_feats(feats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    for meta in list_backgrounds(include_faerun=True):
        row = get_background(meta["id"])
        if not row:
            continue
        feat_name = str(row.get("feat") or "").strip()
        if not feat_name:
            continue
        key = _feat_key(feat_name)
        if key in feats and feats[key].get("text"):
            continue
        # Faerûn-only feats may only exist as PHB feats under a shorter name
        base_key = normalize_spell_name(feat_name.split("(")[0].strip())
        if base_key in feats and feats[base_key].get("text"):
            feats[key] = {**feats[base_key], "title": feat_name}
            continue
        if str(row.get("source") or "") == "faerun":
            feats[key] = {
                "title": feat_name,
                "category": "Origin Feat (Heroes of Faerûn)",
                "text": (
                    f"{feat_name} is a background origin feat from Heroes of Faerûn. "
                    "See the Heroes of Faerûn rules for prerequisites and full benefits."
                ),
            }
    return feats


def _parse_casting_block(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in ("Casting Time", "Range", "Components", "Component", "Duration"):
        m = re.search(rf"{re.escape(key)}:\s*(.+?)(?:\n|$)", body)
        if m:
            norm = "components" if key == "Component" else key.lower().replace(" ", "_")
            if norm not in fields:
                fields[norm] = _clean(m.group(1))
    return fields


def _parse_level(school_line: str) -> int | None:
    if "cantrip" in school_line.lower():
        return 0
    m = re.search(r"Level\s+(\d+)", school_line, re.I)
    return int(m.group(1)) if m else None


def _parse_school(school_line: str) -> str:
    m = re.search(
        r"(?:Level \d+ |(?:\d+(?:st|nd|rd|th)-level )?)?"
        r"([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*(?:Cantrip|\(|$)",
        school_line,
    )
    return m.group(1).strip() if m else ""


def _parse_spell_block(title: str, school_line: str, body: str) -> dict[str, Any] | None:
    casting = _parse_casting_block(body)
    desc = body
    dm = re.search(r"Duration:\s*.+?(?:\n\n|\n[A-Z])", body, re.DOTALL)
    if dm:
        desc = body[dm.end() :]
    desc = _clean(desc)
    desc = re.split(r"\nAPPENDIX|\nINDEX\b", desc)[0].strip()
    desc = _clean(desc)
    if not desc or len(desc) < 15:
        return None
    school_line = school_line.replace("Levei", "Level")
    return {
        "title": _clean(title.title()),
        "level": _parse_level(school_line),
        "school": _parse_school(school_line),
        "classes": re.sub(
            r"\s+", " ", school_line[school_line.find("(") + 1 : school_line.rfind(")")]
        ).strip()
        if "(" in school_line
        else "",
        **casting,
        "text": desc,
    }


def extract_spells(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    section = _pages_text(pages, 239, 543)
    start = section.find("SPELL DESCRIPTIONS")
    end = section.find("APPENDIX A")
    if start < 0:
        return {}
    section = section[start : end if end > start else len(section)]

    school_line = _SPELL_SCHOOL_LINE
    header_re = re.compile(
        rf"\n[\(\[]?([A-Z][A-Z0-9'/,\-\(\) \[\]]{{2,}})[\]\)]?\n+({school_line})\n+Casting Time:",
        re.MULTILINE | re.IGNORECASE,
    )
    matches = list(header_re.finditer(section))
    spells: dict[str, dict[str, Any]] = {}

    for i, m in enumerate(matches):
        title = re.sub(r"^[\[\(]+|[\]\)]+$", "", m.group(1)).strip()
        title = re.sub(r"\s+", " ", title)
        school = m.group(2).strip()
        body_start = m.end() - len("Casting Time:")
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        body = section[body_start:body_end]
        row = _parse_spell_block(title, school, body)
        if not row:
            continue
        key = normalize_spell_name(row["title"])
        if key:
            spells[key] = row

    _fill_missing_spells(section, spells)
    return spells


def _all_class_spell_names() -> dict[str, str]:
    """Map normalized spell id -> display name from curated class lists."""
    names: dict[str, str] = {}
    for by_level in (spells_data().get("spell_lists") or {}).values():
        if not isinstance(by_level, dict):
            continue
        for spell_list in by_level.values():
            if not isinstance(spell_list, list):
                continue
            for name in spell_list:
                display = str(name).strip()
                if display:
                    names[normalize_spell_name(display)] = display
    return names


def _normalize_apostrophes(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").replace("`", "'")


def _title_search_patterns(display_name: str) -> list[str]:
    """OCR-tolerant uppercase patterns for spell headers."""
    display_name = _normalize_apostrophes(display_name)
    words = re.sub(r"[^a-zA-Z0-9' ]+", " ", display_name).split()
    if not words:
        return []
    patterns: list[str] = []
    exact = re.sub(r"\s+", " ", display_name.upper()).strip()
    patterns.append(re.escape(exact))
    patterns.append(re.escape(f"({exact}"))
    if len(words) >= 1:
        suffix = r"[\s\[\]\(\).'\"-]*".join(re.escape(w.upper()) for w in words)
        patterns.append(rf"[^\n]{{0,40}}{suffix}")
    if len(words) == 1:
        patterns.append(re.escape(words[0].upper()))
    elif len(words) >= 2:
        fuzzy = r"[\s\[\]\(\).'\"-]*".join(re.escape(w.upper()) for w in words)
        patterns.append(fuzzy)
        if len(words) == 2:
            patterns.append(
                rf"{re.escape(words[0][:3].upper())}\w*[\s.']+"
                rf"{re.escape(words[1][:3].upper())}\w*\.?"
            )
        if len(words) == 3:
            patterns.append(
                rf"{re.escape(words[0][:3].upper())}\w*[\s.']+"
                rf"{re.escape(words[1][:3].upper())}\w*[\s.']+"
                rf"{re.escape(words[2][:3].upper())}\w*"
            )
    seen: set[str] = set()
    out: list[str] = []
    for p in patterns:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _stub_spell(display_name: str) -> dict[str, Any]:
    from backend.games.dnd5e.characters.spell_resources import build_spell_index

    key = normalize_spell_name(display_name)
    level = build_spell_index().get(key)
    level_label = "Cantrip" if level == 0 else f"Level {level}" if level else "PHB 2024"
    return {
        "title": display_name,
        "level": level,
        "text": (
            f"{display_name} ({level_label}). "
            "Description not available in OCR extract; "
            "use rules search or the PHB spell list during play."
        ),
    }


def _extract_single_spell(section: str, display_name: str) -> dict[str, Any] | None:
    for title_pat in _title_search_patterns(display_name):
        block_re = re.compile(
            rf"\n{title_pat}\n+({_SPELL_SCHOOL_LINE})\n+"
            rf"Casting Time:(.*?)(?=\n[\(\[]?[A-Z]"
            rf"[A-Z0-9'/,\-\(\) ]{{2,}}\n|\Z)",
            re.DOTALL | re.IGNORECASE,
        )
        m = block_re.search(section)
        if m:
            row = _parse_spell_block(display_name, m.group(1).strip(), "Casting Time:" + m.group(2))
            if row:
                return row
    return None


def _fill_missing_spells(section: str, spells: dict[str, dict[str, Any]]) -> None:
    for key, display in _all_class_spell_names().items():
        if key in spells:
            continue
        row = _extract_single_spell(section, display)
        if row:
            spells[key] = row
        else:
            spells[key] = _stub_spell(display)


def _merge_existing_spells(spells: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not OUT_PATH.is_file():
        return spells
    try:
        raw = OUT_PATH.read_text(encoding="utf-8")
        if raw.lstrip().startswith("#"):
            raw = re.sub(r"^#.*\n", "", raw, count=0, flags=re.MULTILINE)
        existing = yaml.safe_load(raw) or {}
    except Exception:
        return spells
    for key, row in (existing.get("spells") or {}).items():
        if key not in spells and isinstance(row, dict) and str(row.get("text") or "").strip():
            spells[key] = row
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
        "acrobatics": "dex",
        "animal_handling": "wis",
        "arcana": "int",
        "athletics": "str",
        "deception": "cha",
        "history": "int",
        "insight": "wis",
        "intimidation": "cha",
        "investigation": "int",
        "medicine": "wis",
        "nature": "int",
        "perception": "wis",
        "performance": "cha",
        "persuasion": "cha",
        "religion": "int",
        "sleight_of_hand": "dex",
        "stealth": "dex",
        "survival": "wis",
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


def _store_feature(
    features: dict[str, dict[str, Any]],
    *,
    title: str,
    text: str,
    level: int | None,
    class_id: str | None,
) -> None:
    title = _canonical_feature_title(title)
    text = _trim_feature_text(_clean(text))
    if len(title) > 80 or re.search(r"^[0-9\s+\-|]+$", title):
        return
    if _is_garbage_feature(title, text):
        return
    key = normalize_spell_name(title)
    if not key:
        return

    title_lower = title.lower()
    if title_lower == "spellcasting":
        inferred = _infer_spellcasting_class_id(text)
        if not inferred:
            return
        class_id = inferred
        level = level or 1

    row: dict[str, Any] = {"title": title, "text": text}
    if level is not None:
        row["level"] = level
    if class_id:
        row["class_id"] = class_id

    if title_lower in _AMBIGUOUS_FEATURES and class_id:
        features[f"{class_id}_{key}"] = row
    elif key not in features:
        features[key] = row


def _extract_warlock_spellcasting(section: str) -> dict[str, dict[str, Any]] | None:
    """Warlock spellcasting often lacks a LEVEL header in OCR."""
    m = re.search(
        r"(?:ability\s+to cast spells\. See chapter 7.*?with Warlock spells.*?)"
        r"(?=Cantrips\.|When you reach Warlock|\nLEVEL\s|\Z)",
        section,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return None
    text = _trim_feature_text(_clean(m.group(0)))
    if len(text) < 40:
        return None
    return {
        "title": "Spellcasting",
        "level": 1,
        "class_id": "warlock",
        "text": text,
    }


def _ensure_curated_feature_stubs(features: dict[str, dict[str, Any]]) -> None:
    for name, stub_text in _KNOWN_FEATURE_STUBS.items():
        key = normalize_spell_name(name)
        existing = features.get(key)
        if existing and not _looks_like_feature_table(str(existing.get("text") or "")):
            continue
        features[key] = {"title": name, "level": 1, "class_id": "wizard", "text": stub_text}


def extract_features(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Class and subclass features from PHB chapter 3."""
    section = _pages_text(pages, 49, 350)
    features: dict[str, dict[str, Any]] = {}

    for m in _LEVEL_FEATURE_RE.finditer(section):
        level = _parse_feature_level(m.group(1))
        title = _canonical_feature_title(m.group(2))
        text = m.group(3)
        class_id = _class_at_pos(section, m.start())
        if title.lower() == "spellcasting" and not level:
            level = 1
        _store_feature(
            features,
            title=title,
            text=text,
            level=level,
            class_id=class_id,
        )

    warlock_row = _extract_warlock_spellcasting(section)
    if warlock_row:
        features["warlock_spellcasting"] = warlock_row

    for name in sorted(_curated_feature_names()):
        key = normalize_spell_name(name)
        existing = features.get(key)
        if existing and not _looks_like_feature_table(str(existing.get("text") or "")):
            continue
        if any(
            isinstance(v, dict)
            and str(v.get("title", "")).lower() == name.lower()
            and not _looks_like_feature_table(str(v.get("text") or ""))
            for v in features.values()
        ):
            continue
        row = _extract_standalone_feature(section, name)
        if row:
            features[key] = row

    _ensure_curated_feature_stubs(features)

    # Drop ambiguous bare entries when class-scoped copies exist.
    for bare in _AMBIGUOUS_FEATURES:
        bkey = normalize_spell_name(bare)
        if bkey not in features:
            continue
        scoped = [k for k in features if k != bkey and k.endswith(bkey) and len(k) > len(bkey)]
        if scoped:
            del features[bkey]

    # Remove subclass-only spellcasting mis-assigned to martial classes.
    for bad in ("fighter_spellcasting", "rogue_spellcasting"):
        features.pop(bad, None)

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


def build_glossary(*, merge_existing: bool = True) -> dict[str, Any]:
    """Build glossary payload from PHB OCR cache. Returns payload dict."""
    pages = _load_ocr_pages()
    spells = extract_spells(pages)
    if merge_existing:
        spells = _merge_existing_spells(spells)
    feats = _split_inline_feats(extract_feats(pages))
    feats = _ensure_background_feats(feats)
    return {
        "source": "player.pdf OCR",
        "spells": spells,
        "skills": extract_skills(pages),
        "feats": feats,
        "features": extract_features(pages),
    }


def write_glossary(payload: dict[str, Any]) -> Path:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# D&D 5e (2024 PHB) glossary for UI tooltips.\n"
        "# Regenerate: python -m scripts.build_glossary_db\n\n"
    )
    OUT_PATH.write_text(
        header + yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    return OUT_PATH


def main() -> None:
    payload = build_glossary()
    write_glossary(payload)
    print(
        f"Wrote {OUT_PATH.name}: "
        f"{len(payload['spells'])} spells, "
        f"{len(payload['skills'])} skills, "
        f"{len(payload['feats'])} feats, "
        f"{len(payload['features'])} features",
    )


if __name__ == "__main__":
    main()
