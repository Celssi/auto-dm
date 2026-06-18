"""D&D 5e PDF source configuration."""

from __future__ import annotations

from backend.config import (
    ALL_FACTIONS,
    CORE_PDFS,
    FAERUN_PDFS,
    OCR_PDFS,
    PDF_SOURCES,
)


def get_pdf_sources() -> dict[str, dict[str, str]]:
    return dict(PDF_SOURCES)


def get_core_pdfs() -> list[str]:
    return list(CORE_PDFS)


def get_faerun_pdfs() -> list[str]:
    return list(FAERUN_PDFS)


def get_ocr_pdfs() -> list[str]:
    return list(OCR_PDFS)


def get_all_factions() -> list[str]:
    return list(ALL_FACTIONS)
