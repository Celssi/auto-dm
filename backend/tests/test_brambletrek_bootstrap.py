"""Brambletrek campaign bootstrap: error mapping and rollback."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.journal_storage import list_campaigns
from backend.routes.play import router as play_router
from backend.storage import list_adventures, list_sessions, save_character


def _save_gnawborn(char_id: str = "bt-boot") -> str:
    save_character(
        char_id,
        {
            "id": char_id,
            "game_id": "brambletrek",
            "name": "QA Bramble",
            "legacy": "seer",
            "health": 13,
            "morale": 19,
            "supplies": 20,
            "active_adventure": "",
        },
    )
    return char_id


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(play_router)
    return TestClient(app, raise_server_exceptions=False)


class _Pkg:
    opening_scene = "Dew on the moss of Hyhill."


def _stub_generation(monkeypatch, *, opening_exc: Exception | None = None):
    llm = MagicMock()
    if opening_exc:
        llm.invoke.side_effect = opening_exc
    else:
        llm.invoke.return_value = _Pkg()
    monkeypatch.setattr(
        "backend.games.brambletrek.dm.bootstrap.structured_llm", lambda *a, **k: llm
    )
    rag = MagicMock(answer="cozy", sources=[])
    monkeypatch.setattr("backend.games.brambletrek.dm.bootstrap.query_rules", lambda *a, **k: rag)
    monkeypatch.setattr(
        "backend.games.brambletrek.dm.bootstrap.generate_opening_summary", lambda **k: "canon"
    )


def test_bootstrap_success_creates_campaign_adventure_session(isolated_saves, monkeypatch):
    _stub_generation(monkeypatch)
    cid = _save_gnawborn()
    res = _client().post(
        "/api/play/bootstrap",
        json={"character_id": cid, "mode": "module", "theme": "", "campaign_name": "QA camp"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["campaign_id"] == "qa-camp"
    assert any(c["id"] == "qa-camp" for c in list_campaigns())
    assert any(s["id"] == body["session_id"] for s in list_sessions(include_archived=True))


def test_code_bug_is_500_not_dm_unavailable_and_nothing_persisted(isolated_saves, monkeypatch):
    _stub_generation(monkeypatch, opening_exc=TypeError("Cannot instantiate typing.Union"))
    cid = _save_gnawborn()
    res = _client().post(
        "/api/play/bootstrap",
        json={"character_id": cid, "mode": "module", "theme": "", "campaign_name": "QA camp"},
    )
    assert res.status_code == 500
    assert "TypeError" in res.json()["detail"]
    assert "unavailable" not in res.json()["detail"].lower()
    assert list_campaigns() == []
    assert list_adventures() == []


def test_failure_after_persist_rolls_back(isolated_saves, monkeypatch):
    _stub_generation(monkeypatch)

    def boom(**_k):
        raise RuntimeError("disk full")

    monkeypatch.setattr("backend.games.brambletrek.dm.bootstrap.create_session", boom)
    cid = _save_gnawborn()
    res = _client().post(
        "/api/play/bootstrap",
        json={"character_id": cid, "mode": "module", "theme": "", "campaign_name": "QA camp"},
    )
    assert res.status_code == 500
    assert list_campaigns() == []
    assert list_adventures() == []


def test_provider_error_still_friendly_503(isolated_saves, monkeypatch):
    _stub_generation(monkeypatch, opening_exc=RuntimeError("Error code: 529 overloaded"))
    cid = _save_gnawborn()
    res = _client().post(
        "/api/play/bootstrap",
        json={"character_id": cid, "mode": "module", "theme": ""},
    )
    assert res.status_code == 503
    assert "busy" in res.json()["detail"].lower()


def test_rag_answer_uses_langchain_not_llamaindex(monkeypatch):
    from backend.rag import engine

    captured = {}

    class FakeLLM:
        def invoke(self, messages):
            captured["messages"] = messages
            return MagicMock(content="answer text")

    monkeypatch.setattr("backend.llm.get_langchain_chat_llm", lambda *a, **k: FakeLLM())
    monkeypatch.setattr("backend.llm._llm_model_name", lambda llm: "fake", raising=False)
    out = engine._generate_rag_answer("sys", "ctx", "q?", "claude")
    assert out == "answer text"
    assert "ctx" in captured["messages"][1].content
