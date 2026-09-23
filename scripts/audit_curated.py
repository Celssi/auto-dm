#!/usr/bin/env python3
"""Audit curated D&D 5e data against core PDFs (backgrounds + spot checks).

Runs structural validation first, then PDF-backed comparison via
``backend.games.dnd5e.curated_audit``.

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

from backend.config import CORE_PDFS, FAERUN_PDFS, pdf_path
from backend.games.dnd5e.curated_audit import run_curated_audit


def _check_pdfs_present() -> list[str]:
    missing: list[str] = []
    for rel in CORE_PDFS + FAERUN_PDFS:
        if not pdf_path(rel).exists():
            missing.append(rel)
    return missing


def pdf_background_audit(source: str, *, limit: int = 0, force_ocr: bool = False) -> list[str]:
    from backend.games.dnd5e.characters.background_extract import (
        diff_background,
        extract_background,
        load_curated_backgrounds,
        load_pdf_pages,
    )

    issues: list[str] = []
    specs = load_curated_backgrounds(source)
    if limit > 0:
        specs = specs[:limit]

    pages = load_pdf_pages(source, force_ocr=force_ocr)
    total = len(specs)
    for i, spec in enumerate(specs, 1):
        if spec.verified_from_pdf:
            print(f"  [{i}/{total}] {spec.label} — skip (verified_from_pdf)", flush=True)
            continue
        print(f"  [{i}/{total}] {spec.label}...", flush=True)
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
            print(f"       error: {extracted['error']}", flush=True)
        elif diffs:
            print(f"       {len(diffs)} mismatch(es)", flush=True)
        else:
            print("       OK", flush=True)
        for d in diffs:
            issues.append(f"[{source}] {spec.label}: {d}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit curated D&D 5e YAML against PDFs")
    parser.add_argument(
        "--skip-pdf", action="store_true", help="Structural checks only (no LLM/OCR)"
    )
    parser.add_argument(
        "--include-faerun", action="store_true", help="Also audit Heroes of Faerûn backgrounds"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit PDF spot/background checks per source"
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Re-run OCR instead of data/ocr_cache/ (normally shared with ingest)",
    )
    args = parser.parse_args()

    print("=== Validator scripts ===")
    for script in ("scripts.validate_dnd5e_character", "scripts.validate_glossary"):
        proc = subprocess.run(
            [sys.executable, "-m", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        print(proc.stdout.strip())

    missing_pdfs = _check_pdfs_present()
    if missing_pdfs:
        print(f"\nMissing PDFs: {', '.join(missing_pdfs)}")

    rc = run_curated_audit(
        skip_pdf=args.skip_pdf,
        limit=args.limit,
        force_ocr=args.force_ocr,
    )
    if rc != 0 or args.skip_pdf:
        if args.include_faerun and not args.skip_pdf:
            pass
        else:
            return rc

    pdf_issues: list[str] = []
    if args.include_faerun and pdf_path("dnd5e/heroes_faerun.pdf").exists():
        print("\n=== PDF audit: Heroes of Faerûn backgrounds ===")
        pdf_issues.extend(
            pdf_background_audit("heroes_faerun", limit=args.limit, force_ocr=args.force_ocr)
        )

    if pdf_issues:
        print(f"\nFaerûn PDF mismatches ({len(pdf_issues)}):")
        for issue in pdf_issues:
            print(f"  - {issue}")
        return 1

    return rc


if __name__ == "__main__":
    sys.exit(main())
