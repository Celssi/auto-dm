#!/usr/bin/env python3
"""Extract background feat/skill/tool data from PDFs via OCR + RAG + LLM.

Examples:
  # Preview Heroes of Faerûn backgrounds (uses RAG if indexed, else OCR cache)
  python -m scripts.extract_backgrounds --source heroes_faerun --dry-run

  # Apply updates to dnd5e_faerun.yaml
  python -m scripts.extract_backgrounds --source heroes_faerun --apply

  # Audit PHB backgrounds against player.pdf
  python -m scripts.extract_backgrounds --source player --audit-only

  # Force fresh OCR (slow)
  python -m scripts.extract_backgrounds --source player --force-ocr --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.games.dnd5e.characters.background_extract import (  # noqa: E402
    PDF_KEYS,
    BackgroundSpec,
    apply_backgrounds_to_yaml,
    diff_background,
    extract_background,
    load_curated_backgrounds,
    load_pdf_pages,
)
from backend.rag.ocr import OcrNotAvailableError  # noqa: E402
from backend.rag.retrieval_core import get_collection


def _print_report(title: str, rows: list[dict]) -> None:
    print(f"\n=== {title} ===")
    ok = sum(1 for r in rows if not r.get("diffs") and not r.get("error"))
    print(f"OK: {ok}/{len(rows)}")
    for row in rows:
        label = row["label"]
        if row.get("error"):
            print(f"  ✗ {label}: {row['error']}")
            continue
        if row.get("diffs"):
            print(f"  △ {label}:")
            for d in row["diffs"]:
                print(f"      - {d}")
        else:
            print(f"  ✓ {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract D&D backgrounds from PDFs")
    parser.add_argument(
        "--source",
        choices=list(PDF_KEYS.keys()),
        default="heroes_faerun",
        help="Which PDF/curated set to process",
    )
    parser.add_argument("--apply", action="store_true", help="Write results into curated YAML")
    parser.add_argument(
        "--dry-run", action="store_true", help="Write preview YAML only (default without --apply)"
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Compare PDF extraction to curated without writing",
    )
    parser.add_argument("--force-ocr", action="store_true", help="Re-run OCR instead of cache")
    parser.add_argument("--no-rag", action="store_true", help="Skip RAG retrieval")
    parser.add_argument("--no-ocr", action="store_true", help="Skip OCR page search")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N backgrounds")
    parser.add_argument("--id", dest="bg_id", default="", help="Single background id")
    parser.add_argument("--json-out", default="", help="Write full report JSON to path")
    parser.add_argument("--provider", default="claude", choices=["claude", "ollama"])
    args = parser.parse_args()

    dry_run = not args.apply or args.dry_run or args.audit_only
    specs = load_curated_backgrounds(args.source)
    if args.bg_id:
        specs = [s for s in specs if s.id == args.bg_id]
    if args.limit > 0:
        specs = specs[: args.limit]

    if not specs:
        print("No backgrounds matched.", file=sys.stderr)
        return 1

    indexed = get_collection() is not None and get_collection().count() > 0
    print(f"Source: {args.source} ({len(specs)} backgrounds)")
    print(
        "RAG index: "
        f"{'ready' if indexed else 'not indexed — run: python -m scripts.ingest --include-faerun'}"
    )

    pages = None
    if not args.no_ocr:
        print("Loading PDF pages (OCR cache or native text)...")
        try:
            pages = load_pdf_pages(args.source, force_ocr=args.force_ocr)
            print(f"  {len(pages)} pages with text")
        except OcrNotAvailableError as e:
            if args.no_rag:
                print(str(e), file=sys.stderr)
                return 1
            print(f"  OCR skipped: {e}")
            pages = None

    report: list[dict] = []
    updates: list[tuple[BackgroundSpec, dict]] = []

    for spec in specs:
        print(f"  → {spec.label}...", flush=True)
        extracted = extract_background(
            spec,
            pdf_key=args.source,
            pages=pages,
            use_rag=not args.no_rag,
            use_ocr=not args.no_ocr,
            force_ocr=args.force_ocr,
            provider=args.provider,
        )
        diffs = diff_background(spec, extracted)
        row = {
            "id": spec.id,
            "label": spec.label,
            "curated": spec.to_yaml_dict(),
            "extracted": extracted,
            "diffs": diffs,
            "error": extracted.get("error"),
        }
        report.append(row)
        updates.append((spec, extracted))

    _print_report(f"Background audit: {args.source}", report)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nReport written to {args.json_out}")

    if args.audit_only:
        mismatches = [r for r in report if r.get("diffs") or r.get("error")]
        return 1 if mismatches else 0

    out = apply_backgrounds_to_yaml(args.source, updates, dry_run=dry_run)
    print(f"\n{'Preview' if dry_run else 'Updated'} YAML: {out}")
    if dry_run and not args.apply:
        print("Re-run with --apply to write into curated file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
