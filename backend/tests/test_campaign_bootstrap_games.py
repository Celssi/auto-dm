"""Tests for campaign bootstrap game isolation."""

from __future__ import annotations

import pytest

from backend.dm.campaign_bootstrap import _require_campaign_plan


def test_brambletrek_rejects_campaign_plan():
    with pytest.raises(ValueError, match="not supported"):
        _require_campaign_plan({"game_id": "brambletrek", "name": "Gnaw"})


def test_dnd_allows_campaign_plan():
    _require_campaign_plan({"game_id": "dnd5e", "name": "Larry"})
