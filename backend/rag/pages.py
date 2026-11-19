"""Printed vs PDF page mapping for rulebooks.

Index metadata `page` stays the 1-based PDF page so Brambletrek boosts keep
working. Citations and the in-app reader use printed pages.
"""

from __future__ import annotations

# PHB 2024: printed N is PDF page N+2 (cover + interior title).
# Brambletrek CDE: printed N is PDF page N-1 (see retrieval._brambletrek_pdf_page).
PHB_PDF_MINUS_PRINTED = 2
BRAMBLETREK_PRINTED_MINUS_PDF = 1

# Player's Handbook 2024 index (PDF pages, 1-based). Printed 379-384.
PHB_INDEX_PDF_PAGES = frozenset(range(381, 387))


def source_key(source_file: str) -> str:
    return (source_file or "").replace("\\", "/").lower()


def is_phb_source(source_file: str) -> bool:
    key = source_key(source_file)
    return key.endswith("player.pdf") or key.endswith("dnd5e/player.pdf")


def is_brambletrek_source(source_file: str) -> bool:
    return "brambletrek" in source_key(source_file)


def pdf_to_printed(source_file: str, pdf_page: int | str | None) -> int:
    try:
        page = max(1, int(pdf_page or 1))
    except (TypeError, ValueError):
        page = 1
    if is_phb_source(source_file):
        return max(1, page - PHB_PDF_MINUS_PRINTED)
    if is_brambletrek_source(source_file):
        return page + BRAMBLETREK_PRINTED_MINUS_PDF
    return page


def printed_to_pdf(source_file: str, printed_page: int | str | None) -> int:
    try:
        page = max(1, int(printed_page or 1))
    except (TypeError, ValueError):
        page = 1
    if is_phb_source(source_file):
        return page + PHB_PDF_MINUS_PRINTED
    if is_brambletrek_source(source_file):
        return max(1, page - BRAMBLETREK_PRINTED_MINUS_PDF)
    return page


def is_skipped_index_page(source_file: str, pdf_page: int | str | None) -> bool:
    """PHB index rows beat short mastery chunks in BM25/rerank; do not index them."""
    try:
        page = int(pdf_page or 0)
    except (TypeError, ValueError):
        return False
    return is_phb_source(source_file) and page in PHB_INDEX_PDF_PAGES
