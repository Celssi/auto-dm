"""Remove pytest artifacts that leaked into the real saves directory."""

from __future__ import annotations

import backend.config as config
from backend.journal_storage import delete_campaign, list_campaigns
from backend.saves_paths import configure_saves_root
from backend.storage import delete_character, get_character

# Campaigns created by backend/tests/test_campaign_*.py and related suites.
TEST_CAMPAIGN_IDS = frozenset(
    {
        "source",
        "test-arc-rogue",
        "test-arc-rogue-2",
        "camp",
        "camp-1",
        "test-camp",
    }
)

TEST_CAMPAIGN_NAMES = frozenset(
    {
        "Test Arc",
        "Test Arc (Rogue)",
        "Test Campaign",
        "Camp",
        "Test",
    }
)

# Fixture character ids written by campaign copy / cascade tests.
TEST_CHARACTER_IDS = frozenset({"hero", "rogue"})

TEST_ADVENTURE_IDS = frozenset(
    {
        "adv1",
        "adv2",
        "test-arc-rogue-chapter-one",
        "test-arc-rogue-chapter-two",
        "test-arc-rogue-2-chapter-one",
        "test-arc-rogue-2-chapter-two",
    }
)


def cleanup_leaked_test_artifacts() -> dict[str, list[str]]:
    """Delete known test campaigns, adventures, and fixture characters from disk."""
    configure_saves_root(config.SAVES_DIR)

    removed_campaigns: list[str] = []
    for row in list_campaigns():
        cid = str(row.get("id") or "")
        name = str(row.get("name") or "")
        if cid in TEST_CAMPAIGN_IDS or name in TEST_CAMPAIGN_NAMES:
            if delete_campaign(cid):
                removed_campaigns.append(cid)

    from backend.storage import delete_adventure

    removed_adventures: list[str] = []
    for adv_id in TEST_ADVENTURE_IDS:
        if delete_adventure(adv_id):
            removed_adventures.append(adv_id)

    removed_characters: list[str] = []
    for char_id in TEST_CHARACTER_IDS:
        if get_character(char_id) and delete_character(char_id):
            removed_characters.append(char_id)

    return {
        "campaigns": removed_campaigns,
        "adventures": removed_adventures,
        "characters": removed_characters,
    }
