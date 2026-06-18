"""Campaign repair and journal backfill tests."""

import tempfile
from pathlib import Path

import backend.config as cfg
from backend.dm.campaign_repair import (
    JournalExtractSpec,
    JournalEntryExtract,
    WAKING_DEEP_ENCOUNTERS,
    WAKING_DEEP_NPCS,
    repair_campaign,
    save_journal_entries,
)
from backend.dm.encounters import load_adventure_encounters
from backend.journal_storage import get_campaign_npc, list_campaign_npcs, save_campaign
from backend.storage import save_adventure


def test_save_journal_entries_writes_npcs():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.journal_storage as js

    js.SAVES_DIR = tmpdir
    campaign_id = "camp-1"
    save_campaign(campaign_id, {"name": "Test Campaign"})
    save_journal_entries(
        campaign_id,
        JournalExtractSpec(
            npcs=[JournalEntryExtract(name="Captain Venn", body="A bold privateer.")],
            locations=[],
        ),
    )
    npcs = list_campaign_npcs(campaign_id)
    assert len(npcs) == 1
    assert npcs[0]["name"] == "Captain Venn"


def test_repair_waking_deep_hardcoded_data():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.journal_storage as js
    import backend.storage as storage

    js.SAVES_DIR = tmpdir
    storage.ADVENTURES_DIR = tmpdir / "adventures"
    storage.ADVENTURES_INDEX = storage.ADVENTURES_DIR / "index.json"
    storage.ADVENTURES_DIR.mkdir(parents=True, exist_ok=True)

    campaign_id = "the-waking-deep-tides-of-the-shattered-crown"
    save_campaign(
        campaign_id, {"name": "The Waking Deep", "story_arc": "Marceska hunts the Crown."}
    )
    for adv_id in WAKING_DEEP_ENCOUNTERS:
        save_adventure(adv_id, {"name": adv_id, "campaign_id": campaign_id}, outline="# Outline")

    result = repair_campaign(campaign_id, use_llm=False)

    assert result["counts"]["npcs"] == len(WAKING_DEEP_NPCS)
    assert result["counts"]["encounters"] == sum(len(v) for v in WAKING_DEEP_ENCOUNTERS.values())
    assert get_campaign_npc(campaign_id, "captain-marceska-venn") is not None
    encounters = load_adventure_encounters("the-drowned-bargain")
    assert any(e.name == "Merrow Harbor Raid" for e in encounters)
