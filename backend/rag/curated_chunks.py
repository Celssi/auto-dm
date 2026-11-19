"""Synthetic RAG documents from curated 2024 YAML so tables survive ingest."""

from __future__ import annotations

from llama_index.core import Document

from backend.games.dnd5e.characters.character_data import list_armor, list_weapons
from backend.games.dnd5e.characters.creation_choices import weapon_mastery_data
from backend.games.dnd5e.dm.structured_lookup import rules_glossary
from backend.rag.ingest_docs import make_rule_document

_PHB = "dnd5e/player.pdf"
_PHB_LABEL = "Player's Handbook (2024)"


def _phb_doc(
    *,
    text: str,
    printed_page: int,
    section_title: str,
    faction: str = "player",
) -> Document:
    pdf_page = printed_page + 2
    return make_rule_document(
        text=text,
        metadata={
            "source_file": _PHB,
            "source_label": _PHB_LABEL,
            "page": str(pdf_page),
            "pdf_page": str(pdf_page),
            "printed_page": str(printed_page),
            "faction": faction,
            "extraction": "curated",
            "page_extraction": "curated",
            "section_title": section_title,
        },
    )


def curated_reference_documents() -> list[Document]:
    """One chunk per weapon, armor, mastery property, and rules-glossary entry."""
    docs: list[Document] = []
    for weapon in list_weapons():
        label = str(weapon.get("label") or "").strip()
        if not label:
            continue
        props = ", ".join(str(p) for p in (weapon.get("properties") or []))
        mastery = str(weapon.get("mastery") or "").strip()
        text = (
            f"{label} weapon. Damage {weapon.get('damage')} {weapon.get('damage_type')}. "
            f"Category: {weapon.get('category')}. "
            f"Properties: {props or 'none'}. "
            f"Mastery: {mastery or 'none'}."
        )
        docs.append(
            _phb_doc(
                text=text,
                printed_page=215,
                section_title=f"{label} (Weapons table)",
            )
        )
    for armor in list_armor():
        label = str(armor.get("label") or "").strip()
        if not label or str(armor.get("id") or "") == "none":
            continue
        parts = [
            f"{label} armor. Category: {armor.get('category')}. Base AC {armor.get('base_ac')}.",
        ]
        if armor.get("add_dex"):
            parts.append("Add Dexterity modifier.")
        if armor.get("dex_cap") is not None:
            parts.append(f"Dexterity bonus capped at {armor.get('dex_cap')}.")
        if armor.get("strength"):
            parts.append(f"Strength {armor.get('strength')} required.")
        docs.append(
            _phb_doc(
                text=" ".join(parts),
                printed_page=219,
                section_title=f"{label} (Armor table)",
            )
        )
    props = weapon_mastery_data().get("properties") or {}
    for key, row in props.items():
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or key).strip()
        summary = str(row.get("summary") or "").strip()
        if not summary:
            continue
        docs.append(
            _phb_doc(
                text=f"{label} weapon mastery property. {summary}",
                printed_page=214,
                section_title=f"{label} (Mastery Properties)",
            )
        )
    for key, row in rules_glossary().items():
        title = str(row.get("title") or key).strip()
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            printed = int(row.get("page") or 214)
        except (TypeError, ValueError):
            printed = 214
        docs.append(
            _phb_doc(
                text=f"{title}. {text}",
                printed_page=printed,
                section_title=title,
            )
        )
    return docs
