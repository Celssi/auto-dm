"""Ingest D&D 5e PDFs into Chroma via LlamaIndex embeddings."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from pypdf import PdfReader

from backend.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DOCS_DIR,
    EMBED_HF_MODEL,
    pdf_path,
)
from backend.embeddings import build_embed_model
from backend.rag.chunking import chunk_page_with_sections
from backend.rag.ingest_docs import make_rule_document
from backend.rag.ocr import (
    OcrNotAvailableError,
    extract_pages_with_ocr,
    needs_ocr,
    ocr_pdf_page_indices,
    tesseract_available,
)
from backend.rag.pages import is_skipped_index_page, pdf_to_printed
from backend.rag.plugin import get_core_pdfs, get_faerun_pdfs, get_ocr_pdfs, get_pdf_sources
from backend.rag.progress import ocr_progress_callback
from backend.rag.text_utils import clean_text, is_low_quality


def extract_pages_pypdf(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        cleaned = clean_text(raw)
        if cleaned:
            pages.append((i + 1, cleaned))
    return pages


def extract_pages_pymupdf(pdf_path: Path) -> list[tuple[int, str]]:
    """Layout-aware text: keeps table rows together better than pypdf."""
    try:
        import fitz
    except ImportError:
        return []
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []
    pages: list[tuple[int, str]] = []
    try:
        for i, page in enumerate(doc):
            raw = page.get_text("text", sort=True) or ""
            cleaned = clean_text(raw)
            if cleaned:
                pages.append((i + 1, cleaned))
    finally:
        doc.close()
    return pages


def _pdf_key(pdf_path: Path) -> str:
    """Return dnd5e/foo.pdf or brambletrek/foo.pdf style key for OCR list matching."""
    parts = pdf_path.parts
    if "dnd5e" in parts:
        idx = parts.index("dnd5e")
        return "/".join(parts[idx:])
    if "brambletrek" in parts:
        idx = parts.index("brambletrek")
        return "/".join(parts[idx:])
    return pdf_path.name


def extract_pages(
    pdf_path: Path,
    use_ocr: bool = True,
    force_ocr: bool = False,
    ocr_pdfs: list[str] | None = None,
) -> tuple[list[tuple[int, str, str]], str]:
    layout_pages = extract_pages_pymupdf(pdf_path)
    if layout_pages:
        seed_pages = layout_pages
        seed_method = "pymupdf"
    else:
        seed_pages = extract_pages_pypdf(pdf_path)
        seed_method = "pypdf"
    page_map: dict[int, str] = {page_num: txt for page_num, txt in seed_pages if txt}
    methods: dict[int, str] = {
        page_num: seed_method for page_num, _ in seed_pages if page_num in page_map
    }

    ocr_pdfs = ocr_pdfs or []
    key = _pdf_key(pdf_path)
    should_ocr_doc = use_ocr and (force_ocr or needs_ocr(pdf_path) or key in ocr_pdfs)

    if use_ocr:
        try:
            if force_ocr or (should_ocr_doc and not page_map):
                ocr_pages = extract_pages_with_ocr(pdf_path, force=force_ocr)
                page_map = {page_num: txt for page_num, txt in ocr_pages if txt}
                methods = {page_num: "ocr" for page_num in page_map}
            else:
                total_pages = len(PdfReader(str(pdf_path)).pages)
                weak_pages = [
                    page_num
                    for page_num, text in page_map.items()
                    if is_low_quality(text, min_chars=60, min_alpha_ratio=0.2)
                ]
                missing_pages = [p for p in range(1, total_pages + 1) if p not in page_map]
                target_pages = sorted(set(weak_pages + missing_pages))
                if target_pages and (should_ocr_doc or bool(weak_pages) or bool(missing_pages)):
                    print(
                        f"    OCR fallback: {len(target_pages)} pages "
                        f"({len(missing_pages)} missing, {len(weak_pages)} low quality)"
                    )
                    ocr_pages = ocr_pdf_page_indices(
                        pdf_path,
                        target_pages,
                        progress_callback=ocr_progress_callback(f"{pdf_path.name} (partial)"),
                    )
                    for page_num, ocr_text in ocr_pages:
                        base = page_map.get(page_num, "")
                        prefer_ocr = (
                            not base
                            or is_low_quality(base, min_chars=60, min_alpha_ratio=0.2)
                            or len(ocr_text) > int(len(base) * 1.2)
                        )
                        if prefer_ocr:
                            page_map[page_num] = ocr_text
                            methods[page_num] = "ocr"
        except OcrNotAvailableError as e:
            print(f"    OCR ERROR: {e}")

    pages = [
        (p, t, methods.get(p, "pypdf"))
        for p, t in sorted(page_map.items())
        if t and len(t.strip()) >= 10
    ]
    if not pages:
        return [], "none"

    method_values = set(method for _, _, method in pages)
    if len(method_values) == 1:
        extraction = next(iter(method_values))
    else:
        extraction = "hybrid"
    return pages, extraction


def build_documents(
    path: Path,
    meta: dict[str, str],
    use_ocr: bool = True,
    force_ocr: bool = False,
    ocr_pdfs: list[str] | None = None,
) -> list[Document]:
    pages, extraction = extract_pages(
        path,
        use_ocr=use_ocr,
        force_ocr=force_ocr,
        ocr_pdfs=ocr_pdfs,
    )
    docs: list = []
    source_file = _pdf_key(path)
    for page_num, page_text, page_extraction in pages:
        if is_skipped_index_page(source_file, page_num):
            continue
        printed = pdf_to_printed(source_file, page_num)
        for section_title, chunk in chunk_page_with_sections(page_text, CHUNK_SIZE, CHUNK_OVERLAP):
            chunk_meta = {
                "source_file": source_file,
                "source_label": meta["label"],
                "page": str(page_num),
                "pdf_page": str(page_num),
                "printed_page": str(printed),
                "faction": meta["faction"],
                "extraction": extraction,
                "page_extraction": page_extraction,
                "section_title": section_title,
            }
            docs.append(make_rule_document(text=chunk, metadata=chunk_meta))
    return docs


def load_pdf_list(*, core_only: bool = True, include_faerun: bool = False) -> list[str]:
    if core_only and not include_faerun:
        return get_core_pdfs()
    pdfs = list(get_core_pdfs())
    if include_faerun:
        pdfs.extend(get_faerun_pdfs())
    return pdfs


def preflight_ingest(*, pdf_names: list[str], use_ocr: bool) -> list[str]:
    """Return fatal error messages; empty list means OK to proceed."""
    errors: list[str] = []

    if use_ocr:
        ocr_needed = any(needs_ocr(pdf_path(name)) for name in pdf_names if pdf_path(name).exists())
        if ocr_needed and not tesseract_available():
            errors.append(
                "Tesseract OCR not installed (needed for scanned PDFs). Run: brew install tesseract"
            )

    return errors


def run_ingest(
    *,
    core_only: bool = True,
    include_faerun: bool = False,
    reset: bool = True,
    use_ocr: bool = True,
    force_ocr: bool = False,
    game_id: str = "dnd5e",
    skip_audit: bool = False,
) -> int:
    from backend.games.registry import get_game

    plugin = get_game(game_id)
    if plugin.rag.run_ingest:
        return plugin.rag.run_ingest(
            core_only=core_only,
            include_faerun=include_faerun,
            reset=reset,
            use_ocr=use_ocr,
            force_ocr=force_ocr,
            game_id=game_id,
            skip_audit=skip_audit,
        )

    pdf_sources = get_pdf_sources()
    ocr_pdfs = get_ocr_pdfs()
    pdf_names = load_pdf_list(core_only=core_only, include_faerun=include_faerun)
    preflight_errors = preflight_ingest(pdf_names=pdf_names, use_ocr=use_ocr)
    if preflight_errors:
        for msg in preflight_errors:
            print(f"PREFLIGHT ERROR: {msg}", file=sys.stderr)
        return 1

    all_docs = []

    present = [name for name in pdf_names if pdf_path(name).exists()]
    for name in pdf_names:
        if name not in present:
            print(f"SKIP (missing): {name} at {pdf_path(name)}")

    if not present:
        print("No PDF files found to index.")
        return 1

    print(f"Indexing {len(present)} PDFs...")

    for idx, name in enumerate(present, 1):
        path = pdf_path(name)
        meta = pdf_sources.get(name, {"faction": "core", "label": name})
        print(f"\n[{idx}/{len(present)}] {name}")
        page_docs = build_documents(
            path,
            meta,
            use_ocr=use_ocr,
            force_ocr=force_ocr,
            ocr_pdfs=ocr_pdfs,
        )
        print(f"  {name}: {len(page_docs)} chunks")
        if len(page_docs) == 0:
            print(
                f"    WARNING: no text extracted from {name}. "
                "Install Tesseract (brew install tesseract) and re-run with --ocr."
            )
        all_docs.extend(page_docs)

    from backend.rag.curated_chunks import curated_reference_documents

    curated_docs = curated_reference_documents()
    print(f"  curated tables/glossary: {len(curated_docs)} chunks")
    all_docs.extend(curated_docs)

    if not all_docs:
        print("No documents to index.")
        return 1

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    embed_model = build_embed_model()

    print(f"\nEmbedding {len(all_docs)} chunks with {EMBED_HF_MODEL}...")
    VectorStoreIndex.from_documents(
        all_docs,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    print(f"Done. Index '{COLLECTION_NAME}' stored in {CHROMA_DIR}")
    from backend.gcs_sync import upload_chroma

    upload_chroma()
    if not skip_audit:
        _build_glossary_after_ingest()
        return _audit_dnd5e_curated_after_ingest(skip_pdf=True)
    print("Curated audit: skipped")
    return 0


def _audit_dnd5e_curated_after_ingest(*, skip_pdf: bool = True) -> int:
    from backend.games.dnd5e.curated_audit import run_curated_audit

    print("")
    return run_curated_audit(skip_pdf=skip_pdf)


def _audit_brambletrek_curated_after_ingest(*, skip_pdf: bool = False) -> int:
    from backend.games.brambletrek.curated_audit import run_curated_audit

    print("")
    return run_curated_audit(skip_pdf=skip_pdf)


def run_brambletrek_ingest(
    *,
    reset: bool = True,
    use_ocr: bool = True,
    force_ocr: bool = False,
    skip_audit: bool = False,
) -> int:
    return _run_brambletrek_ingest(
        reset=reset,
        use_ocr=use_ocr,
        force_ocr=force_ocr,
        skip_audit=skip_audit,
    )


def _run_brambletrek_ingest(
    *,
    reset: bool = True,
    use_ocr: bool = True,
    force_ocr: bool = False,
    skip_audit: bool = False,
) -> int:
    from backend.games.brambletrek.rag_config import COLLECTION, MVP_PDFS, get_pdf_sources

    collection_name = COLLECTION
    pdf_sources = get_pdf_sources()
    pdf_names = list(MVP_PDFS)
    preflight_errors = preflight_ingest(pdf_names=pdf_names, use_ocr=use_ocr)
    if preflight_errors:
        for msg in preflight_errors:
            print(f"PREFLIGHT ERROR: {msg}", file=sys.stderr)
        return 1

    present = [name for name in pdf_names if pdf_path(name).exists()]
    for name in pdf_names:
        if name not in present:
            print(f"SKIP (missing): {name} at {pdf_path(name)}")

    if not present:
        print("No Brambletrek PDF files found to index.")
        return 1

    all_docs = []
    print(f"Indexing {len(present)} Brambletrek PDFs...")
    for idx, name in enumerate(present, 1):
        path = pdf_path(name)
        meta = pdf_sources.get(name, {"faction": "core", "label": name})
        print(f"\n[{idx}/{len(present)}] {name}")
        page_docs = build_documents(
            path,
            meta,
            use_ocr=use_ocr,
            force_ocr=force_ocr,
            ocr_pdfs=[],
        )
        all_docs.extend(page_docs)
        print(f"  -> {len(page_docs)} chunks")

    if not all_docs:
        print("No text extracted from Brambletrek PDFs.")
        return 1

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embed_model = build_embed_model()
    print(f"\nEmbedding {len(all_docs)} chunks with {EMBED_HF_MODEL}...")
    VectorStoreIndex.from_documents(
        all_docs,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    print(f"Done. Index '{collection_name}' stored in {CHROMA_DIR}")
    from backend.gcs_sync import upload_chroma

    upload_chroma()
    if skip_audit:
        print("Curated audit: skipped")
        return 0
    return _audit_brambletrek_curated_after_ingest()


def _build_glossary_after_ingest() -> None:
    """Rebuild tooltip glossary from PHB OCR cache (created during ingest)."""
    from backend.config import OCR_CACHE_DIR

    player_cache = OCR_CACHE_DIR / "player.json"
    if not player_cache.is_file():
        print("\nGlossary: skipped (no PHB OCR cache — index player.pdf first)")
        return
    print("\n=== Glossary (UI tooltips) ===")
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.build_glossary_db"],
        cwd=Path(__file__).resolve().parents[2],
    )
    if proc.returncode != 0:
        print("WARNING: glossary build failed (tooltips may be incomplete)", file=sys.stderr)


def main() -> None:
    from backend.games.registry import get_game, list_games

    game_ids = [g["id"] for g in list_games()]
    parser = argparse.ArgumentParser(description="Index D&D 5e PDFs into Chroma")
    parser.add_argument("--core", action="store_true", help="Index PHB + DMG + MM only (default)")
    parser.add_argument(
        "--include-faerun",
        action="store_true",
        help="Also index Heroes of Faerûn and Adventures in Faerûn",
    )
    parser.add_argument("--no-reset", action="store_true", help="Append without deleting index")
    parser.add_argument("--ocr", action="store_true", help="Force OCR refresh")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback")
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Skip curated YAML audit after ingest / glossary build",
    )
    parser.add_argument(
        "--game",
        default="dnd5e",
        choices=game_ids,
        help="Game to index (default: dnd5e)",
    )
    args = parser.parse_args()
    plugin = get_game(args.game)
    if plugin.rag.run_ingest:
        print(f"Ingest {plugin.label} from {DOCS_DIR}")
        sys.exit(
            run_ingest(
                reset=not args.no_reset,
                use_ocr=not args.no_ocr,
                force_ocr=args.ocr,
                game_id=args.game,
                skip_audit=args.skip_audit,
            )
        )
    include_faerun = args.include_faerun
    core_only = not include_faerun or args.core
    label = (
        "core" if core_only and not include_faerun else ("core+faerun" if include_faerun else "all")
    )
    print(f"Ingest D&D 5e ({label}) from {DOCS_DIR}")
    sys.exit(
        run_ingest(
            core_only=core_only and not include_faerun,
            include_faerun=include_faerun,
            reset=not args.no_reset,
            use_ocr=not args.no_ocr,
            force_ocr=args.ocr,
        )
    )


if __name__ == "__main__":
    main()
