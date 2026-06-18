"""Cascade delete behavior for campaigns, adventures, and characters."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend import journal_storage, storage


@pytest.fixture
def saves_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(storage, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(journal_storage, "SAVES_DIR", tmp_path)
    storage.CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    storage.ADVENTURES_DIR.mkdir(parents=True, exist_ok=True)
    storage.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    journal_storage.CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    yield tmp_path


def test_delete_adventure_cascades_sessions(saves_dir: Path):
    storage.save_character("hero", {"name": "Hero"})
    adv_id = storage.save_adventure("adv1", {"name": "Quest", "character_id": "hero"})
    session_id = storage.create_session(character_id="hero", adventure_id=adv_id)

    assert storage.delete_adventure(adv_id)
    assert storage.get_adventure(adv_id) is None
    assert storage.get_session(session_id) is None


def test_delete_campaign_cascades_adventures_and_sessions(saves_dir: Path):
    storage.save_character("hero", {"name": "Hero"})
    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": ["hero"]})
    adv_id = storage.save_adventure(
        "adv1", {"name": "Quest", "campaign_id": "camp", "character_id": "hero"}
    )
    session_id = storage.create_session(character_id="hero", adventure_id=adv_id)

    assert journal_storage.delete_campaign("camp")
    assert journal_storage.get_campaign("camp") is None
    assert storage.get_adventure(adv_id) is None
    assert storage.get_session(session_id) is None
    assert storage.get_character("hero") is not None


def test_delete_character_cascades_adventures_sessions_and_campaign_refs(saves_dir: Path):
    storage.save_character("hero", {"name": "Hero"})
    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": ["hero"]})
    adv_id = storage.save_adventure(
        "adv1", {"name": "Quest", "campaign_id": "camp", "character_id": "hero"}
    )
    session_id = storage.create_session(character_id="hero", adventure_id=adv_id)

    assert storage.delete_character("hero")
    assert storage.get_character("hero") is None
    assert storage.get_adventure(adv_id) is None
    assert storage.get_session(session_id) is None
    camp = journal_storage.get_campaign("camp")
    assert camp is not None
    assert camp.get("character_ids") == []
