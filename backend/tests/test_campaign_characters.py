"""Campaign ↔ character linking."""

from backend import journal_storage, storage


def test_resolve_character_ids_from_adventures(isolated_saves):
    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": []})
    storage.save_adventure(
        "adv1",
        {"name": "Quest", "character_id": "hero", "campaign_id": "camp"},
    )

    ids = journal_storage.resolve_campaign_character_ids("camp", persist=True)
    assert ids == ["hero"]
    assert journal_storage.get_campaign("camp")["character_ids"] == ["hero"]


def test_save_adventure_links_character_to_campaign(isolated_saves):
    journal_storage.save_campaign("camp", {"name": "Camp"})
    storage.save_adventure(
        "adv1",
        {"name": "Quest", "character_id": "hero", "campaign_id": "camp"},
    )

    assert journal_storage.get_campaign("camp")["character_ids"] == ["hero"]
