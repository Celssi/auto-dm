#!/usr/bin/env python3
"""Structural validation for dnd5e_glossary.yaml (UI tooltips).

Checks coverage against spell lists, skills, backgrounds, and class features.
Does not OCR-compare spell text (use build_glossary_db to regenerate from PHB OCR).

Examples:
  python -m scripts.validate_glossary
  python -m scripts.validate_glossary --strict   # fail on warnings too
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.characters.character_data import (  # noqa: E402
    get_background,
    list_backgrounds,
    skills_data,
    spells_data,
)
from backend.characters.features import class_features_data, subclass_features_data  # noqa: E402
from backend.characters.glossary_data import glossary_data  # noqa: E402
from backend.characters.spell_resources import normalize_spell_name  # noqa: E402
from backend.config import CURATED_DIR, DATA_DIR  # noqa: E402
from backend.glossary import build_glossary_index, lookup_entry  # noqa: E402

GLOSSARY_PATH = CURATED_DIR / "dnd5e_glossary.yaml"
OCR_PLAYER = DATA_DIR / "ocr_cache" / "player.json"

GENERIC_FEATURE_NAMES = {
    "subclass feature",
    "ability score improvement",
    "epic boon",
}

MIN_COUNTS = {
    "spells": 250,
    "skills": 18,
    "feats": 50,
    "features": 200,
}


def _spell_names_in_lists() -> set[str]:
    names: set[str] = set()
    for by_level in (spells_data().get("spell_lists") or {}).values():
        if not isinstance(by_level, dict):
            continue
        for spell_list in by_level.values():
            if not isinstance(spell_list, list):
                continue
            for name in spell_list:
                names.add(normalize_spell_name(str(name)))
    return names


def _background_feat_names() -> set[str]:
    names: set[str] = set()
    for meta in list_backgrounds(include_faerun=True):
        row = get_background(meta["id"])
        if not row:
            continue
        feat = str(row.get("feat") or "").strip()
        if feat:
            names.add(feat)
    return names


def _curated_feature_names() -> set[str]:
    names: set[str] = set()
    for levels in (class_features_data().get("classes") or {}).values():
        if not isinstance(levels, dict):
            continue
        for feature_list in levels.values():
            if not isinstance(feature_list, list):
                continue
            for name in feature_list:
                label = str(name).strip()
                if label and label.lower() not in GENERIC_FEATURE_NAMES:
                    names.add(label)
    for row in (subclass_features_data().get("subclasses") or {}).values():
        if not isinstance(row, dict):
            continue
        for feature_list in (row.get("features") or {}).values():
            if not isinstance(feature_list, list):
                continue
            for name in feature_list:
                label = str(name).strip()
                if label and label.lower() not in GENERIC_FEATURE_NAMES:
                    names.add(label)
    return names


def _ambiguous_feature_titles(data: dict) -> list[str]:
    """Feature titles reused across classes (only one wins in glossary YAML)."""
    title_classes: dict[str, set[str]] = {}
    for cid, levels in (class_features_data().get("classes") or {}).items():
        if not isinstance(levels, dict):
            continue
        for feature_list in levels.values():
            if not isinstance(feature_list, list):
                continue
            for name in feature_list:
                label = str(name).strip()
                if not label or label.lower() in GENERIC_FEATURE_NAMES:
                    continue
                title_classes.setdefault(label, set()).add(str(cid))

    ambiguous = [title for title, classes in title_classes.items() if len(classes) > 1]
    # Only flag if glossary has a single shared entry for that title.
    features = data.get("features") or {}
    flagged: list[str] = []
    for title in ambiguous:
        key = normalize_spell_name(title)
        if key in features:
            flagged.append(title)
    return sorted(flagged)


def _feature_class_ids(name: str) -> list[str]:
    """Classes that list this feature in curated data."""
    label = name.strip()
    if not label:
        return []
    classes: set[str] = set()
    for cid, levels in (class_features_data().get("classes") or {}).items():
        if not isinstance(levels, dict):
            continue
        for feature_list in levels.values():
            if not isinstance(feature_list, list):
                continue
            if label in (str(n).strip() for n in feature_list):
                classes.add(str(cid))
    for row in (subclass_features_data().get("subclasses") or {}).values():
        if not isinstance(row, dict):
            continue
        for feature_list in (row.get("features") or {}).values():
            if not isinstance(feature_list, list):
                continue
            if label in (str(n).strip() for n in feature_list):
                sc = str(row.get("class_id") or row.get("class") or "")
                if sc:
                    classes.add(sc)
    return sorted(classes)


def _looks_like_ocr_garbage(text: str) -> bool:
    if len(text) < 40:
        return False
    markers = (
        "Subclass feature Ability Score",
        "Ability Score Improvement 4d6",
        "Proficiency Level Bonus Class Features",
    )
    return any(m in text for m in markers)


def validate_glossary(*, strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not GLOSSARY_PATH.is_file():
        errors.append(f"Missing glossary file: {GLOSSARY_PATH}")
        return errors, warnings

    data = glossary_data()
    if not data:
        errors.append("Glossary YAML is empty or failed to parse")
        return errors, warnings

    for section, minimum in MIN_COUNTS.items():
        count = len(data.get(section) or {})
        if count < minimum:
            errors.append(f"Glossary {section}: expected at least {minimum}, got {count}")

    skill_ids = [
        str(s.get("id") or "")
        for s in (skills_data().get("skills") or [])
        if isinstance(s, dict) and s.get("id")
    ]
    glossary_skills = data.get("skills") or {}
    for sid in skill_ids:
        row = glossary_skills.get(sid)
        if not isinstance(row, dict) or not str(row.get("text") or "").strip():
            errors.append(f"Skill tooltip missing text: {sid}")

    spell_names = _spell_names_in_lists()
    glossary_spells = data.get("spells") or {}
    missing_spell_rows = sorted(n for n in spell_names if n not in glossary_spells)
    if missing_spell_rows:
        sample = ", ".join(missing_spell_rows[:8])
        errors.append(
            f"{len(missing_spell_rows)} class-list spell(s) missing from glossary YAML (e.g. {sample})"
        )

    empty_spell_text = sorted(
        key
        for key, row in glossary_spells.items()
        if isinstance(row, dict) and len(str(row.get("text") or "").strip()) < 20
    )
    if empty_spell_text:
        warnings.append(f"{len(empty_spell_text)} glossary spell(s) have very short text")

    index = build_glossary_index()
    missing_tooltip: list[str] = []
    for nk in sorted(spell_names):
        display = next(
            (
                str(n)
                for by_level in (spells_data().get("spell_lists") or {}).values()
                if isinstance(by_level, dict)
                for spell_list in by_level.values()
                if isinstance(spell_list, list)
                for n in spell_list
                if normalize_spell_name(str(n)) == nk
            ),
            nk,
        )
        if not lookup_entry(display, use_rag=False).get("summary"):
            missing_tooltip.append(display)
    if missing_tooltip:
        sample = ", ".join(missing_tooltip[:8])
        errors.append(
            f"{len(missing_tooltip)} class-list spell(s) have no tooltip summary (e.g. {sample})"
        )

    for feat_name in sorted(_background_feat_names()):
        if not lookup_entry(feat_name, use_rag=False).get("summary"):
            warnings.append(f"Background feat tooltip missing: {feat_name}")

    missing_features: list[str] = []
    for name in sorted(_curated_feature_names()):
        class_ids = _feature_class_ids(name)
        if len(class_ids) == 1:
            has_summary = bool(
                lookup_entry(name, use_rag=False, class_id=class_ids[0]).get("summary")
            )
        elif class_ids:
            has_summary = any(
                lookup_entry(name, use_rag=False, class_id=cid).get("summary") for cid in class_ids
            )
        else:
            has_summary = bool(lookup_entry(name, use_rag=False).get("summary"))
        if not has_summary:
            missing_features.append(name)
    if missing_features:
        sample = ", ".join(missing_features[:8])
        warnings.append(
            f"{len(missing_features)} class/subclass feature(s) have no tooltip summary (e.g. {sample})"
        )

    ambiguous = _ambiguous_feature_titles(data)
    for title in ambiguous:
        warnings.append(
            f"Ambiguous shared feature title in glossary (one entry, many classes): {title}"
        )

    garbage_features = [
        str(row.get("title") or key)
        for key, row in (data.get("features") or {}).items()
        if isinstance(row, dict) and _looks_like_ocr_garbage(str(row.get("text") or ""))
    ]
    if garbage_features:
        sample = ", ".join(garbage_features[:5])
        warnings.append(
            f"{len(garbage_features)} feature tooltip(s) look like OCR table bleed (e.g. {sample})"
        )

    if OCR_PLAYER.is_file() and GLOSSARY_PATH.is_file():
        if OCR_PLAYER.stat().st_mtime > GLOSSARY_PATH.stat().st_mtime:
            warnings.append(
                "OCR cache is newer than dnd5e_glossary.yaml — run: python -m scripts.build_glossary_db"
            )

    if strict:
        errors.extend(warnings)
        warnings = []

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate glossary / tooltip curated data")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    errors, warnings = validate_glossary(strict=args.strict)

    if warnings:
        print(f"Glossary warnings ({len(warnings)}):")
        for issue in warnings:
            print(f"  - {issue}")

    if errors:
        print(f"Glossary errors ({len(errors)}):")
        for issue in errors:
            print(f"  - {issue}")
        print("\nFix: python -m scripts.build_glossary_db  (after rules ingest / OCR cache exists)")
        return 1

    print("Glossary validation: OK")
    if warnings:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
