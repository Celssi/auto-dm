"""Tests for pytest artifact cleanup."""

from __future__ import annotations

from backend.tests.artifact_cleanup import (
    TEST_CAMPAIGN_IDS,
    TEST_CAMPAIGN_NAMES,
    cleanup_leaked_test_artifacts,
)


def test_cleanup_targets_known_test_campaign_ids():
    assert "source" in TEST_CAMPAIGN_IDS
    assert "camp" in TEST_CAMPAIGN_IDS
    assert "Test Arc" in TEST_CAMPAIGN_NAMES


def test_cleanup_runs_without_error(isolated_saves):
    from backend import journal_storage, storage

    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": []})
    storage.save_character("rogue", {"name": "Rogue"})

    result = cleanup_leaked_test_artifacts()
    assert "camp" in result["campaigns"]
    assert journal_storage.get_campaign("camp") is None
