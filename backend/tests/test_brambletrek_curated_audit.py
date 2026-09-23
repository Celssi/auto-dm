"""Tests for Brambletrek curated audit."""

from __future__ import annotations

from backend.config import pdf_path
from backend.games.brambletrek.curated_audit import (
    CORE_PDF_KEY,
    _journey_printed_page,
    compact_text,
    pdf_audit,
    run_curated_audit,
    structural_audit,
    text_found_in_page,
)


def test_structural_audit_passes() -> None:
    assert structural_audit() == []


def test_text_found_in_page_normalizes_whitespace() -> None:
    body = "Every year, your village holds a grand festival"
    page = "Every year, your\nvillage holds a grand\nfestival, the Harvest's Dawn."
    assert text_found_in_page(body, page)


def test_compact_text_strips_punctuation() -> None:
    assert compact_text("Hunt for the Elixir!") == "huntfortheelixir"


def test_journey_printed_page_maps_suit_to_module_page() -> None:
    cde_pages = [105, 106, 107, 108]
    assert _journey_printed_page(cde_pages, "hearts") == 105
    assert _journey_printed_page(cde_pages, "clubs") == 108
    winter_gift_pages = [3, 4]
    assert _journey_printed_page(winter_gift_pages, "hearts") == 3
    assert _journey_printed_page(winter_gift_pages, "clubs") == 4


def test_pdf_audit_when_core_pdf_present() -> None:
    if not pdf_path(CORE_PDF_KEY).exists():
        return
    issues = pdf_audit(limit=3)
    assert issues == []


def test_run_curated_audit_skip_pdf() -> None:
    assert run_curated_audit(skip_pdf=True) == 0
