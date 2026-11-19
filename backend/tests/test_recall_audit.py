import json

import pytest

from backend.rag.recall_audit import (
    QUERIES_PATH,
    compact_report,
    load_recall_report,
    save_recall_report,
    score_sources,
)


def test_score_sources_hits_on_title():
    sources = [
        {
            "section_title": "Exhaustion",
            "text": "The target has a penalty.",
            "printed_page": "366",
        }
    ]
    scored = score_sources(
        sources,
        {
            "id": "exhaustion-what",
            "expect_title": "Exhaustion",
            "expect_terms": ["d20", "speed"],
            "printed_page": 366,
        },
    )
    assert scored["hit"] is True
    assert scored["title_hit"] is True
    assert scored["terms_hit"] is False
    assert scored["page_hit"] is True


def test_score_sources_hits_on_all_terms():
    sources = [
        {
            "section_title": "Mastery Properties",
            "text": "Cleave: extra melee attack once per turn.",
            "printed_page": "214",
        }
    ]
    scored = score_sources(
        sources,
        {
            "id": "mastery-cleave",
            "expect_title": "Cleave",
            "expect_terms": ["melee", "once per turn"],
            "printed_page": 214,
        },
    )
    assert scored["hit"] is True
    assert scored["terms_hit"] is True


def test_score_sources_miss_without_title_or_terms():
    sources = [{"section_title": "Unrelated", "text": "Something else", "printed_page": "10"}]
    scored = score_sources(
        sources,
        {
            "id": "heroic-inspiration",
            "expect_title": "Heroic Inspiration",
            "expect_terms": ["reroll"],
            "printed_page": 13,
        },
    )
    assert scored["hit"] is False
    assert scored["page_hit"] is False


def test_saruman_query_file_is_packaged():
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    assert len(queries) >= 20
    assert queries[0]["id"] == "exhaustion-what"


def test_save_and_load_recall_report(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.config.SAVES_DIR", tmp_path)
    report = {
        "game_id": "dnd5e",
        "chunk_count": 12,
        "hits": 18,
        "total": 20,
        "recall": 0.9,
        "page_hits": 10,
        "page_recall": 0.5,
        "misses": ["healing-word-fireball"],
        "page_misses": ["heroic-inspiration"],
        "results": [
            {
                "id": "exhaustion-what",
                "hit": True,
                "page_hit": True,
                "query": "What does Exhaustion do?",
                "top_sections": ["Exhaustion"],
                "top_pages": ["366"],
            }
        ],
    }
    compact = save_recall_report(report, upload=False)
    assert compact["hits"] == 18
    loaded = load_recall_report()
    assert loaded is not None
    assert loaded["misses"] == ["healing-word-fireball"]
    assert loaded["results"][0]["top_pages"] == ["366"]
    assert compact_report(report)["total"] == 20


def test_recall_audit_endpoint_is_public(monkeypatch):
    pytest.importorskip("chromadb")
    from fastapi.testclient import TestClient

    from backend.main import app
    from backend.routes import system

    monkeypatch.setattr(
        system,
        "_index_status",
        lambda: {"indexed_by_game": {"dnd5e": True}, "indexed": True, "chunk_counts": {"dnd5e": 1}},
    )
    monkeypatch.setattr(system, "_cached_recall", lambda: None)
    monkeypatch.setattr(
        system,
        "_run_and_cache_recall",
        lambda: {"hits": 19, "total": 20, "recall": 0.95, "misses": ["healing-word-fireball"]},
    )
    response = TestClient(app).get("/api/recall-audit?refresh=1")
    assert response.status_code == 200
    assert response.json()["hits"] == 19


def test_recall_audit_endpoint_requires_index(monkeypatch):
    pytest.importorskip("chromadb")
    from fastapi.testclient import TestClient

    from backend.main import app
    from backend.routes import system

    monkeypatch.setattr(
        system,
        "_index_status",
        lambda: {"indexed_by_game": {"dnd5e": False}, "indexed": False, "chunk_counts": {}},
    )
    response = TestClient(app).get("/api/recall-audit")
    assert response.status_code == 503
