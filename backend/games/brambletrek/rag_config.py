"""Brambletrek RAG and PDF configuration."""

from __future__ import annotations

GAME_ID = "brambletrek"
COLLECTION = "brambletrek_rules"

PDF_SOURCES: dict[str, dict[str, str]] = {
    "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf": {
        "faction": "core",
        "label": "Brambletrek Complete Digital Edition",
    },
    "brambletrek/Brambletrek_-_A_Birthday_of_Wonders.pdf": {
        "faction": "adventure",
        "label": "Brambletrek: A Birthday of Wonders",
    },
    "brambletrek/Brambletrek_-_Winter_Gift.pdf": {
        "faction": "adventure",
        "label": "Brambletrek: Winter Gift",
    },
}

MVP_PDFS = [
    "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf",
    "brambletrek/Brambletrek_-_A_Birthday_of_Wonders.pdf",
    "brambletrek/Brambletrek_-_Winter_Gift.pdf",
]

ALL_FACTIONS = ["core", "adventure"]


def get_pdf_sources() -> dict[str, dict[str, str]]:
    return dict(PDF_SOURCES)


def get_all_factions() -> list[str]:
    return list(ALL_FACTIONS)
