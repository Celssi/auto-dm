"""Ingest D&D 5e PDFs into Chroma via LlamaIndex + Ollama embeddings."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from pypdf import PdfReader

from backend.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DOCS_DIR,
    EMBED_DOCUMENT_PREFIX,
    EMBED_MODEL,
    EMBED_QUERY_PREFIX,
    OLLAMA_BASE_URL,
    pdf_path,
)
from backend.rag.ocr import (
    OcrNotAvailableError,
    extract_pages_with_ocr,
    needs_ocr,
    ocr_pdf_page_indices,
    tesseract_available,
)
from backend.rag.plugin import get_core_pdfs, get_faerun_pdfs, get_ocr_pdfs, get_pdf_sources
from backend.rag.progress import ocr_progress_callback
from backend.rag.text_utils import clean_text, is_low_quality, is_meaningful


def _keep_chunk(text: str) -> bool:
    if is_meaningful(text, min_chars=25, min_alpha_ratio=0.12):
        return True
    compact = re.sub(r"\s+", "", text)
    has_letters = bool(re.search(r"[A-Za-z]{3,}", text))
    has_numbers = bool(re.search(r"\d", text))
    return len(compact) >= 20 and has_letters and has_numbers


def _hard_split(text: str, chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    if len(paragraph) <= chunk_size:
        return [paragraph]
    sentence_parts = re.split(r"(?<=[.!?])\s+", paragraph)
    if len(sentence_parts) <= 1:
        return _hard_split(paragraph, chunk_size)
    out: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for sent in sentence_parts:
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) > chunk_size:
            if buf:
                out.append(" ".join(buf))
                buf = []
                buf_len = 0
            out.extend(_hard_split(sent, chunk_size))
            continue
        add_len = len(sent) + (1 if buf else 0)
        if buf and buf_len + add_len > chunk_size:
            out.append(" ".join(buf))
            buf = [sent]
            buf_len = len(sent)
        else:
            buf.append(sent)
            buf_len += add_len
    if buf:
        joined = " ".join(buf)
        if len(joined) > chunk_size:
            out.extend(_hard_split(joined, chunk_size))
        else:
            out.append(joined)
    return out


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if _keep_chunk(text) else []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    expanded: list[str] = []
    for para in paragraphs:
        expanded.extend(_split_long_paragraph(para, chunk_size))

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for part in expanded:
        add_len = len(part) + (2 if current else 0)
        if current and current_len + add_len > chunk_size:
            chunks.append("\n\n".join(current).strip())
            if overlap > 0:
                tail = chunks[-1][-overlap:].strip()
                current = [tail, part] if tail else [part]
                current_len = len("\n\n".join(current))
            else:
                current = [part]
                current_len = len(part)
            continue
        current.append(part)
        current_len += add_len
    if current:
        chunks.append("\n\n".join(current).strip())

    capped: list[str] = []
    for chunk in chunks:
        capped.extend(_hard_split(chunk, chunk_size))
    return [c for c in capped if _keep_chunk(c)]


def extract_pages_pypdf(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        cleaned = clean_text(raw)
        if cleaned:
            pages.append((i + 1, cleaned))
    return pages


def _pdf_key(pdf_path: Path) -> str:
    """Return dnd5e/foo.pdf style key for OCR list matching."""
    parts = pdf_path.parts
    if "dnd5e" in parts:
        idx = parts.index("dnd5e")
        return "/".join(parts[idx:])
    return pdf_path.name


def extract_pages(
    pdf_path: Path,
    use_ocr: bool = True,
    force_ocr: bool = False,
    ocr_pdfs: list[str] | None = None,
) -> tuple[list[tuple[int, str, str]], str]:
    pypdf_pages = extract_pages_pypdf(pdf_path)
    page_map: dict[int, str] = {page_num: txt for page_num, txt in pypdf_pages if txt}
    methods: dict[int, str] = {
        page_num: "pypdf" for page_num, _ in pypdf_pages if page_num in page_map
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
    if method_values == {"ocr"}:
        extraction = "ocr"
    elif method_values == {"pypdf"}:
        extraction = "pypdf"
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
    docs: list[Document] = []
    source_file = _pdf_key(path)
    for page_num, page_text, page_extraction in pages:
        for chunk in _chunk_text(page_text, CHUNK_SIZE, CHUNK_OVERLAP):
            chunk_meta = {
                "source_file": source_file,
                "source_label": meta["label"],
                "page": str(page_num),
                "faction": meta["faction"],
                "extraction": extraction,
                "page_extraction": page_extraction,
            }
            docs.append(Document(text=chunk, metadata=chunk_meta))
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

    try:
        import ollama

        models = {m.model for m in ollama.list().models}
        # ollama may return "nomic-embed-text" or "nomic-embed-text:latest"
        if not any(m == EMBED_MODEL or m.startswith(f"{EMBED_MODEL}:") for m in models):
            errors.append(
                f'Ollama embedding model "{EMBED_MODEL}" not found. Run: ollama pull {EMBED_MODEL}'
            )
    except Exception as e:
        errors.append(f"Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}")

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
) -> int:
    pdf_sources = get_pdf_sources()
    ocr_pdfs = get_ocr_pdfs()
    pdf_names = load_pdf_list(core_only=core_only, include_faerun=include_faerun)
    preflight_errors = preflight_ingest(pdf_names=pdf_names, use_ocr=use_ocr)
    if preflight_errors:
        for msg in preflight_errors:
            print(f"PREFLIGHT ERROR: {msg}", file=sys.stderr)
        return 1

    all_docs: list[Document] = []

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

    embed_model = OllamaEmbedding(
        model_name=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
        text_instruction=EMBED_DOCUMENT_PREFIX,
        query_instruction=EMBED_QUERY_PREFIX,
    )

    print(f"\nEmbedding {len(all_docs)} chunks with {EMBED_MODEL}...")
    VectorStoreIndex.from_documents(
        all_docs,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )
    print(f"Done. Index '{COLLECTION_NAME}' stored in {CHROMA_DIR}")
    _build_glossary_after_ingest()
    return 0


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
    args = parser.parse_args()
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
