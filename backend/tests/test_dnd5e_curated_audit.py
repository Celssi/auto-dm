"""Tests for D&D 5e curated audit."""

from __future__ import annotations

from backend.config import pdf_path
from backend.games.dnd5e.curated_audit import (
    PLAYER_PDF_KEY,
    equipment_consistency_audit,
    run_curated_audit,
    structural_audit,
)


def test_structural_audit_passes() -> None:
    assert structural_audit() == []


def test_equipment_greatsword_is_2d6() -> None:
    assert equipment_consistency_audit() == []


def test_run_curated_audit_skip_pdf() -> None:
    assert run_curated_audit(skip_pdf=True) == 0


def test_pdf_spot_audit_when_phb_present() -> None:
    if not pdf_path(PLAYER_PDF_KEY).exists():
        return
    from backend.config import OCR_CACHE_DIR
    from backend.games.dnd5e.curated_audit import pdf_spot_audit

    if not (OCR_CACHE_DIR / "player.json").exists():
        return
    issues = pdf_spot_audit(limit=2)
    assert isinstance(issues, list)
