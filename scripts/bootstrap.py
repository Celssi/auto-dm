#!/usr/bin/env python3
"""Bootstrap auto-dm: check deps and optionally index PDFs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from backend.config import PDF_DIR
    from backend.rag.retrieval_core import get_collection

    pdfs = list(PDF_DIR.glob("*.pdf"))
    print(f"auto-dm bootstrap — PDF dir: {PDF_DIR} ({len(pdfs)} files)")
    collection = get_collection()
    if collection and collection.count() > 0:
        print(f"Index ready: {collection.count()} chunks")
        return 0
    print("No index found. Run ingest (this may take hours with OCR):")
    print("  python -m scripts.ingest --core")
    print("Optional Faerûn supplements:")
    print("  python -m scripts.ingest --include-faerun")
    if "--index" in sys.argv:
        from backend.rag.ingest import run_ingest

        include_faerun = "--include-faerun" in sys.argv
        return run_ingest(core_only=not include_faerun, include_faerun=include_faerun)
    return 0


if __name__ == "__main__":
    sys.exit(main())
