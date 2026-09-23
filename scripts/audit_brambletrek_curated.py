#!/usr/bin/env python3
"""Audit curated Brambletrek YAML against the Core Rulebook PDF.

Examples:
  python -m scripts.audit_brambletrek_curated
  python -m scripts.audit_brambletrek_curated --skip-pdf
  python -m scripts.audit_brambletrek_curated --limit 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.games.brambletrek.curated_audit import run_curated_audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit curated Brambletrek YAML")
    parser.add_argument("--skip-pdf", action="store_true", help="Structural checks only")
    parser.add_argument("--limit", type=int, default=0, help="Limit PDF rows checked")
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Re-run OCR instead of data/ocr_cache/",
    )
    args = parser.parse_args()
    return run_curated_audit(
        skip_pdf=args.skip_pdf,
        limit=args.limit,
        force_ocr=args.force_ocr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
