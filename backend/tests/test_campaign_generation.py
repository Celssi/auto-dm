"""Campaign generation: mocked LLM end-to-end, no live Anthropic or Chroma."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if "chromadb" not in sys.modules:
    sys.modules["chromadb"] = MagicMock()

from backend.dm.campaign_bootstrap import (  # noqa: E402
    CampaignPlanSpec,
    JournalEntrySpec,
    PlannedAdventureSpec,
    generate_campaign_with_plan,
)
from backend.dm.errors import friendly_dm_error
from backend.journal_storage import get_campaign
from backend.routes.play import router as play_router
from backend.storage import list_adventures_for_campaign, save_character


@pytest.fixture(autouse=True)
def disable_gcs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTO_DM_BUCKET", "")


def _plan() -> CampaignPlanSpec:
    return CampaignPlanSpec(
        campaign_name="Mill Shadows",
        story_arc=(
            "A quiet mill town hides a pact with river spirits. The hero uncovers the bargain, "
            "faces the miller who feeds it, and chooses whether the town keeps its luck."
        ),
        adventures=[
            PlannedAdventureSpec(
                name="The First Grinding",
                theme="Strange grain and missing cats",
                outline="Premise: the mill never stops.\nAct 1: ask around.\nPossible ending: the hopper opens.",
                sequence=1,
            ),
            PlannedAdventureSpec(
                name="River Debt",
                theme="The spirit wants a name",
                outline="Premise: the river rises.\nAct 1: a night watch.\nPossible ending: a name is given.",
                sequence=2,
            ),
            PlannedAdventureSpec(
                name="Last Harvest",
                theme="Break or keep the pact",
                outline="Premise: harvest night.\nAct 1: the miller waits.\nPossible ending: the wheel stills.",
                sequence=3,
            ),
        ],
        npcs=[JournalEntrySpec(name="Miller Brann", body="Tired, flour-dusted, hiding a debt.")],
        locations=[JournalEntrySpec(name="Red Wheel Mill", body="A water mill that never sleeps.")],
    )


def _save_wizard() -> str:
    return save_character(
        "gen-wiz",
        {
            "id": "gen-wiz",
            "name": "QA Wizard",
            "game_id": "dnd5e",
            "species": "human",
            "class_name": "wizard",
            "level": 1,
            "hp": 8,
            "max_hp": 8,
            "ability_scores": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
            "classes": [{"class_name": "wizard", "level": 1}],
        },
    )


def _stub_character_plugin(monkeypatch):
    plugin = MagicMock()
    plugin.id = "dnd5e"
    monkeypatch.setattr("backend.dm.campaign_bootstrap._plugin_for_character", lambda _char: plugin)
    monkeypatch.setattr("backend.dm.campaign_bootstrap._require_campaign_plan", lambda _char: None)
    monkeypatch.setattr("backend.dm.campaign_bootstrap._char_prompt", lambda _char: "QA Wizard, human wizard 1")


def test_generate_campaign_freeform_mocked_llm(isolated_saves, monkeypatch):
    plan = _plan()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = plan
    monkeypatch.setattr("backend.dm.campaign_bootstrap.structured_llm", lambda *a, **k: mock_llm)
    _stub_character_plugin(monkeypatch)
    char_id = _save_wizard()

    result = generate_campaign_with_plan(
        character_id=char_id,
        mode="freeform",
        theme="haunted mill town",
        adventure_count=3,
        include_faerun=False,
        campaign_name="Mill Shadows",
        bootstrap_first=False,
    )

    assert result["campaign_id"] == "mill-shadows"
    assert result["counts"]["adventures"] == 3
    assert result["counts"]["npcs"] == 1
    campaign = get_campaign("mill-shadows")
    assert campaign is not None
    assert campaign["name"] == "Mill Shadows"
    assert len(list_adventures_for_campaign("mill-shadows")) == 3
    mock_llm.invoke.assert_called_once()


def test_generate_campaign_route_returns_friendly_503(isolated_saves, monkeypatch):
    credit = (
        "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
        "'message': 'Your credit balance is too low to access the Anthropic API. "
        "Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id': 'req_abc'}"
    )
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError(credit)
    monkeypatch.setattr("backend.dm.campaign_bootstrap.structured_llm", lambda *a, **k: mock_llm)
    _stub_character_plugin(monkeypatch)
    _save_wizard()

    app = FastAPI()
    app.include_router(play_router)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/play/generate-campaign",
        json={"character_id": "gen-wiz", "mode": "freeform", "theme": "haunted mill town"},
    )
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "credits exhausted" in detail.lower()
    assert "req_abc" not in detail
    assert "Internal server error" not in detail


def test_friendly_maps_internal_server_error():
    msg = friendly_dm_error("Internal server error")
    assert "unavailable" in msg.lower()
    assert "internal" not in msg.lower()


def test_claude_probe_classifies_credit_error(monkeypatch):
    from backend.llm import probe_claude

    class FakeResponse:
        status_code = 400
        text = (
            "Your credit balance is too low to access the Anthropic API. "
            "Please go to Plans & Billing to upgrade or purchase credits."
        )

    monkeypatch.setattr("backend.llm.resolve_anthropic_api_key", lambda: "sk-test")
    monkeypatch.setattr("backend.llm._PROBE_CACHE", {})

    import httpx

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse())
    result = probe_claude(force=True)
    assert result["ok"] is False
    assert result["class"] == "credits"
    assert result["http_status"] == 400
