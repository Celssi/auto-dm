"""Tesseract OCR for image-only PDFs with JSON cache."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz
import pytesseract
from pypdf import PdfReader
from pytesseract import TesseractNotFoundError

from backend.rag.progress import ocr_progress_callback
from backend.config import (
    OCR_CACHE_DIR,
    OCR_MIN_CHARS_SAMPLE,
    OCR_RENDER_DPI,
    TESSERACT_CONFIG,
    TESSERACT_LANG,
)
from backend.rag.text_utils import clean_text, is_meaningful

# Stay under PIL's decompression bomb limit on oversized PDF pages (e.g. DMG spreads).
_MAX_OCR_PIXELS = 150_000_000

# We already cap rendered pages at _MAX_OCR_PIXELS (and downscale anything larger),
# so raise PIL's decompression-bomb threshold to match. Large rulebook spreads at
# 300 DPI are expected here, not an attack — this just silences the per-page warning.
from PIL import Image as _PILImage  # noqa: E402

_PILImage.MAX_IMAGE_PIXELS = _MAX_OCR_PIXELS


def _open_pdf(pdf_path: Path) -> fitz.Document:
    """Open PDF for rendering; suppress MuPDF structure-tree noise on stderr."""
    fitz.TOOLS.mupdf_display_errors(False)
    return fitz.open(str(pdf_path))


def _render_page_pixmap(page: fitz.Page, dpi: int) -> fitz.Pixmap:
    current_dpi = dpi
    while current_dpi >= 72:
        pix = page.get_pixmap(dpi=current_dpi)
        if pix.width * pix.height <= _MAX_OCR_PIXELS:
            return pix
        current_dpi = int(current_dpi * 0.75)
    return page.get_pixmap(dpi=72)


class OcrNotAvailableError(RuntimeError):
    """Raised when Tesseract is not installed on the system."""


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _cache_path(pdf_path: Path) -> Path:
    return OCR_CACHE_DIR / f"{pdf_path.stem}.json"


def sample_extracted_chars(pdf_path: Path, sample_pages: int = 3) -> int:
    reader = PdfReader(str(pdf_path))
    total = 0
    for i in range(min(sample_pages, len(reader.pages))):
        total += len((reader.pages[i].extract_text() or "").strip())
    return total


def needs_ocr(pdf_path: Path, min_chars: int | None = None) -> bool:
    threshold = min_chars if min_chars is not None else OCR_MIN_CHARS_SAMPLE
    return sample_extracted_chars(pdf_path) < threshold


def ocr_pdf_pages(
    pdf_path: Path,
    dpi: int | None = None,
    progress_callback=None,
) -> list[dict]:
    """Run Tesseract on each page. progress_callback(current, total) optional."""
    if not tesseract_available():
        raise OcrNotAvailableError(
            "Tesseract not found. Install with: brew install tesseract"
        )

    dpi = dpi or OCR_RENDER_DPI
    doc = _open_pdf(pdf_path)
    pages_out: list[dict] = []
    total = len(doc)

    from PIL import Image
    import io

    for i in range(total):
        page = doc[i]
        pix = _render_page_pixmap(page, dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang=TESSERACT_LANG, config=TESSERACT_CONFIG)
        cleaned = clean_text(text)
        if is_meaningful(cleaned, min_chars=40):
            pages_out.append({"page": i + 1, "text": cleaned})
        if progress_callback:
            progress_callback(i + 1, total)

    doc.close()
    return pages_out


def ocr_pdf_page_indices(
    pdf_path: Path,
    page_indices: list[int],
    dpi: int | None = None,
    progress_callback=None,
) -> list[tuple[int, str]]:
    """OCR only selected 1-indexed pages from a PDF."""
    if not page_indices:
        return []
    if not tesseract_available():
        raise OcrNotAvailableError(
            "Tesseract not found. Install with: brew install tesseract"
        )

    dpi = dpi or OCR_RENDER_DPI
    wanted = sorted({p for p in page_indices if p > 0})
    doc = _open_pdf(pdf_path)

    from PIL import Image
    import io

    pages_out: list[tuple[int, str]] = []
    total = len(wanted)
    for idx, page_no in enumerate(wanted):
        idx = page_no - 1
        if idx >= len(doc):
            continue
        pix = _render_page_pixmap(doc[idx], dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang=TESSERACT_LANG, config=TESSERACT_CONFIG)
        cleaned = clean_text(text)
        if is_meaningful(cleaned, min_chars=30, min_alpha_ratio=0.15):
            pages_out.append((page_no, cleaned))
        if progress_callback:
            progress_callback(idx + 1, total)
    doc.close()
    return pages_out


def save_cache(pdf_path: Path, pages: list[dict]) -> Path:
    OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(pdf_path)
    payload = {
        "source_file": pdf_path.name,
        "pages": pages,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_cache(pdf_path: Path) -> list[tuple[int, str]] | None:
    path = _cache_path(pdf_path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(int(p["page"]), p["text"]) for p in data.get("pages", [])]


def load_or_run_ocr(
    pdf_path: Path,
    force: bool = False,
    progress_callback=None,
) -> list[tuple[int, str]]:
    if not force:
        cached = load_cache(pdf_path)
        if cached:
            print(f"    OCR cache hit: {_cache_path(pdf_path).name} ({len(cached)} pages)")
            return cached

    print(f"    Running OCR on {pdf_path.name} ({OCR_RENDER_DPI} dpi)...")
    report = progress_callback or ocr_progress_callback(pdf_path.name)
    try:
        pages = ocr_pdf_pages(pdf_path, progress_callback=report)
    except TesseractNotFoundError as e:
        raise OcrNotAvailableError(
            "Tesseract not found. Install with: brew install tesseract"
        ) from e

    save_cache(pdf_path, pages)
    print(f"    OCR done: {len(pages)} pages with text")
    return [(int(p["page"]), p["text"]) for p in pages]


def extract_pages_with_ocr(
    pdf_path: Path,
    force: bool = False,
    progress_callback=None,
) -> list[tuple[int, str]]:
    return load_or_run_ocr(pdf_path, force=force, progress_callback=progress_callback)
