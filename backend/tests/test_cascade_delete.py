"""Cascade delete behavior for campaigns, adventures, and characters."""

from __future__ import annotations

from backend import journal_storage, storage


def test_delete_adventure_cascades_sessions(isolated_saves):
    storage.save_character("hero", {"name": "Hero"})
    adv_id = storage.save_adventure("adv1", {"name": "Quest", "character_id": "hero"})
    session_id = storage.create_session(character_id="hero", adventure_id=adv_id)

    assert storage.delete_adventure(adv_id)
    assert storage.get_adventure(adv_id) is None
    assert storage.get_session(session_id) is None


def test_delete_campaign_cascades_adventures_and_sessions(isolated_saves):
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


def test_delete_character_cascades_adventures_sessions_and_campaign_refs(isolated_saves):
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
