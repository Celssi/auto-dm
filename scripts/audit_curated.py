#!/usr/bin/env python3
"""Audit curated D&D 5e data against core PDFs (backgrounds + spot checks).

Runs structural validation first, then PDF-backed background comparison for:
  - player.pdf → dnd5e_backgrounds.yaml
  - heroes_faerun.pdf → dnd5e_faerun.yaml (optional)

Examples:
  python -m scripts.audit_curated
  python -m scripts.audit_curated --skip-pdf          # fast structural only
  python -m scripts.audit_curated --include-faerun --limit 3
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.characters.background_extract import (  # noqa: E402
    diff_background,
    extract_background,
    load_curated_backgrounds,
    load_pdf_pages,
)
from backend.characters.character_data import (
    get_background,
    get_class,
    list_backgrounds,
    list_classes,
    list_species,
)
from backend.characters.features import class_features_data, subclass_features_data
from backend.config import pdf_path, CORE_PDFS, FAERUN_PDFS
from backend.rag.retrieval_core import get_collection


def _check_pdfs_present() -> list[str]:
    missing: list[str] = []
    for rel in CORE_PDFS + FAERUN_PDFS:
        if not pdf_path(rel).exists():
            missing.append(rel)
    return missing


def structural_audit() -> list[str]:
    issues: list[str] = []

    if len(list_classes(include_faerun=False)) != 12:
        issues.append(f"Expected 12 PHB classes, got {len(list_classes(include_faerun=False))}")
    if len(list_species()) != 10:
        issues.append(f"Expected 10 PHB species, got {len(list_species())}")
    if len(list_backgrounds(include_faerun=False)) != 16:
        issues.append(f"Expected 16 PHB backgrounds, got {len(list_backgrounds(include_faerun=False))}")

    for cls in list_classes(include_faerun=False):
        cid = cls["id"]
        if not cls.get("hit_die"):
            issues.append(f"Class {cid} missing hit_die")
        if not cls.get("subclasses"):
            issues.append(f"Class {cid} missing subclasses")
        cf = (class_features_data().get("classes") or {}).get(cid)
        if not cf:
            issues.append(f"Class {cid} missing class_features entry")
        subs = subclass_features_data().get("subclasses") or {}
        sub_labels = {
            str(v.get("label", ""))
            for v in subs.values()
            if isinstance(v, dict) and v.get("class_id") == cid
        }
        for sub in cls.get("subclasses") or []:
            if sub not in sub_labels:
                issues.append(f"Subclass feature missing: {cid} / {sub}")

    for bg in list_backgrounds(include_faerun=False):
        row = get_background(bg["id"])
        if not row:
            issues.append(f"Background {bg['id']} not loadable")
            continue
        for key in ("feat", "skills", "tool", "ability_scores"):
            if not row.get(key):
                issues.append(f"Background {bg['id']} missing {key}")

    return issues


def pdf_background_audit(source: str, *, limit: int = 0, force_ocr: bool = False) -> list[str]:
    issues: list[str] = []
    specs = load_curated_backgrounds(source)
    if limit > 0:
        specs = specs[:limit]

    pages = load_pdf_pages(source, force_ocr=force_ocr)
    for spec in specs:
        extracted = extract_background(
            spec,
            pdf_key=source,
            pages=pages,
            use_rag=True,
            use_ocr=True,
            force_ocr=force_ocr,
        )
        diffs = diff_background(spec, extracted)
        if extracted.get("error"):
            issues.append(f"[{source}] {spec.label}: extract error — {extracted['error']}")
        for d in diffs:
            issues.append(f"[{source}] {spec.label}: {d}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit curated D&D 5e YAML against PDFs")
    parser.add_argument("--skip-pdf", action="store_true", help="Structural checks only (no LLM/OCR)")
    parser.add_argument("--include-faerun", action="store_true", help="Also audit Heroes of Faerûn backgrounds")
    parser.add_argument("--limit", type=int, default=0, help="Limit PDF backgrounds checked per source")
    parser.add_argument("--force-ocr", action="store_true")
    args = parser.parse_args()

    print("=== Structural audit ===")
    # Re-use existing validator
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.validate_dnd5e_character"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    print(proc.stdout.strip())

    struct_issues = structural_audit()
    if struct_issues:
        print(f"\nStructural issues ({len(struct_issues)}):")
        for issue in struct_issues:
            print(f"  - {issue}")
    else:
        print("Structural spot-checks: OK")

    missing_pdfs = _check_pdfs_present()
    if missing_pdfs:
        print(f"\nMissing PDFs: {', '.join(missing_pdfs)}")

    if args.skip_pdf:
        return 1 if struct_issues else 0

    collection = get_collection()
    if collection is None or collection.count() == 0:
        print(
            "\nWARNING: Rules not indexed. PDF audit uses OCR + LLM only (slower, less accurate)."
            "\n  Run: python -m scripts.ingest --core  # and --include-faerun for HoF"
        )
    else:
        print(f"\nRAG index: {collection.count()} chunks")

    pdf_issues: list[str] = []
    if pdf_path("dnd5e/player.pdf").exists():
        print("\n=== PDF audit: PHB backgrounds (player.pdf) ===")
        pdf_issues.extend(pdf_background_audit("player", limit=args.limit, force_ocr=args.force_ocr))

    if args.include_faerun and pdf_path("dnd5e/heroes_faerun.pdf").exists():
        print("\n=== PDF audit: Heroes of Faerûn backgrounds ===")
        pdf_issues.extend(
            pdf_background_audit("heroes_faerun", limit=args.limit, force_ocr=args.force_ocr)
        )

    if pdf_issues:
        print(f"\nPDF mismatches ({len(pdf_issues)}):")
        for issue in pdf_issues:
            print(f"  - {issue}")
        print("\nFix with: python -m scripts.extract_backgrounds --source <player|heroes_faerun> --apply")
        return 1

    print("\nPDF background audit: all matched (or none run)")
    return 1 if struct_issues else 0


if __name__ == "__main__":
    sys.exit(main())
