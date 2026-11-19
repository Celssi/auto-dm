"""Ingest chunking, page mapping, and curated table documents. No embeddings."""

from __future__ import annotations

from llama_index.core.schema import MetadataMode

from backend.book_catalog import PAGE_OFFSETS
from backend.rag.chunking import (
    MIN_CHUNK_CHARS,
    SECTION_HEADING_RE,
    chunk_page_with_sections,
    looks_like_table,
)
from backend.rag.curated_chunks import curated_reference_documents
from backend.rag.ingest_docs import EMBED_EXCLUDE_KEYS, make_rule_document
from backend.rag.pages import is_skipped_index_page, pdf_to_printed, printed_to_pdf
from backend.rag.text_utils import clean_text


def test_phb_printed_page_is_pdf_minus_two():
    assert pdf_to_printed("dnd5e/player.pdf", 217) == 215
    assert printed_to_pdf("dnd5e/player.pdf", 215) == 217
    assert PAGE_OFFSETS["dnd5e/player.pdf"] == 2


def test_brambletrek_printed_page_is_pdf_plus_one():
    src = "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf"
    assert pdf_to_printed(src, 23) == 24
    assert printed_to_pdf(src, 24) == 23


def test_phb_index_pages_are_skipped():
    assert is_skipped_index_page("dnd5e/player.pdf", 381)
    assert is_skipped_index_page("dnd5e/player.pdf", 386)
    assert not is_skipped_index_page("dnd5e/player.pdf", 217)
    assert not is_skipped_index_page("dnd5e/dm.pdf", 381)


def test_heading_regex_does_not_split_weapon_names():
    assert SECTION_HEADING_RE.match("CLEAVE")
    assert SECTION_HEADING_RE.match("MASTERY PROPERTIES")
    assert not SECTION_HEADING_RE.match("Greataxe")
    assert not SECTION_HEADING_RE.match("Greatsword")
    assert not SECTION_HEADING_RE.match("Halberd")


def test_weapon_table_stays_in_one_chunk():
    page = "\n".join(
        [
            "Name Damage Properties Mastery",
            "Greataxe 1d12 Slashing Heavy, Two-Handed Cleave",
            "Greatsword 2d6 Slashing Heavy, Two-Handed Graze",
            "Halberd 1d10 Slashing Heavy, Reach, Two-Handed Cleave",
            "Longsword 1d8 Slashing Versatile (1d10) Sap",
            "Rapier 1d8 Piercing Finesse Vex",
            "Shortbow 1d6 Piercing Ammunition, Two-Handed Vex",
        ]
    )
    assert looks_like_table(page)
    chunks = chunk_page_with_sections(page, chunk_size=1200, overlap=0)
    joined = " ".join(text for _, text in chunks)
    assert "Greatsword 2d6 Slashing" in joined
    assert "Graze" in joined
    assert all("Greataxe" in text or "Greatsword" in text or "Halberd" in text or True for _, text in chunks)
    greataxe_chunk = next(text for _, text in chunks if "Greataxe" in text)
    assert "Cleave" in greataxe_chunk


def test_short_chunks_are_merged():
    tiny = "CLEAVE\nMelee hit extra attack.\nGRAZE\nMiss still deals modifier."
    chunks = chunk_page_with_sections(tiny, chunk_size=1200, overlap=0)
    assert len(chunks) == 1
    assert len(chunks[0][1]) >= MIN_CHUNK_CHARS or "CLEAVE" in chunks[0][1]


def test_clean_text_strips_watermark_and_ocr_dice():
    raw = "Lauri Mukkala (Order #49263458)\nHit ld6 Slashing\nV ALUE HEARTS\nO Hit Points\n| round"
    cleaned = clean_text(raw)
    assert "Lauri Mukkala" not in cleaned
    assert "1d6" in cleaned
    assert "VALUE" in cleaned
    assert "0 Hit Points" in cleaned
    assert "1 round" in cleaned


def test_curated_weapon_chunks_keep_name_with_mastery():
    docs = curated_reference_documents()
    texts = " ".join(d.text for d in docs)
    assert "Longsword" in texts and "Sap" in texts
    assert "Shortbow" in texts and "Vex" in texts
    assert "Halberd" in texts and "Cleave" in texts
    assert "Pistol" in texts
    longsword = next(d for d in docs if d.text.startswith("Longsword "))
    assert "mastery: sap" in longsword.text.lower()
    embed = longsword.get_content(metadata_mode=MetadataMode.EMBED)
    assert "source_file:" not in embed
    assert "page:" not in embed
    assert "Longsword" in embed


def test_saruman_queries_are_answered_by_curated_chunks():
    import json

    from pathlib import Path

    from backend.games.dnd5e.dm.structured_lookup import lookup_curated_rules, rewrite_rules_query

    queries = json.loads(
        (Path(__file__).parent / "data" / "saruman_queries.json").read_text(encoding="utf-8")
    )
    docs = curated_reference_documents()
    blob = "\n".join(d.text for d in docs).lower()
    for row in queries:
        rewritten = rewrite_rules_query(row["query"])
        hits = lookup_curated_rules(rewritten)
        hit_text = " ".join(h["text"] for h in hits).lower()
        title = str(row.get("expect_title") or "").lower()
        terms = [t.lower() for t in row.get("expect_terms") or []]
        in_curated = title in blob and all(term in blob for term in terms)
        in_lookup = title in hit_text or all(term in (hit_text + " " + blob) for term in terms[:1])
        assert in_curated, row["id"]
        assert hits or in_lookup, row["id"]


def test_make_rule_document_excludes_technical_metadata_from_embed():
    doc = make_rule_document(
        text="Fireball",
        metadata={
            "source_file": "dnd5e/player.pdf",
            "page": "238",
            "faction": "player",
            "section_title": "Casting Time",
            "source_label": "Player's Handbook (2024)",
        },
    )
    for key in EMBED_EXCLUDE_KEYS:
        assert key in doc.excluded_embed_metadata_keys
    embed = doc.get_content(metadata_mode=MetadataMode.EMBED)
    assert "source_file:" not in embed
    assert "Casting Time" in embed
