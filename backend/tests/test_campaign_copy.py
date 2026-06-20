"""Campaign copy for replay."""

from backend import journal_storage, storage
from backend.dm.campaign_copy import _base_story_arc, copy_campaign
from backend.dm.story_director import Checkpoint, StoryProgress, load_story_progress


def test_base_story_arc_strips_plot_updates():
    arc = "Main plot.\n\n[Plot update]\nSomething happened."
    assert _base_story_arc(arc) == "Main plot."


def test_copy_campaign_resets_for_new_character(tmp_path, monkeypatch):
    monkeypatch.setattr(journal_storage, "SAVES_DIR", tmp_path)
    monkeypatch.setattr(storage, "SAVES_DIR", tmp_path)
    journal_storage.CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    storage.ADVENTURES_DIR.mkdir(parents=True, exist_ok=True)
    storage.CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)

    storage.save_character("hero", {"name": "Hero"})
    storage.save_character("rogue", {"name": "Rogue"})

    journal_storage.save_campaign(
        "source",
        {
            "name": "Test Arc",
            "story_arc": "Premise.\n\n[Plot update]\nPlayed once.",
            "character_ids": ["hero"],
        },
    )
    journal_storage.save_campaign_npc("source", "guide", {"name": "Guide", "body": "Helpful NPC."})

    storage.save_adventure(
        "adv1",
        {
            "name": "Chapter One",
            "character_id": "hero",
            "campaign_id": "source",
            "status": "active",
            "sequence": 1,
        },
        outline="# Outline\n\nBeat one.",
        log="# Adventure log\n\nOld play history.",
    )
    storage.save_adventure(
        "adv2",
        {
            "name": "Chapter Two",
            "character_id": "hero",
            "campaign_id": "source",
            "status": "planned",
            "sequence": 2,
        },
        outline="# Outline\n\nBeat two.",
        log="# Adventure log\n\nMore history.",
    )

    from backend.dm.story_director import save_story_progress

    save_story_progress(
        "adv1",
        StoryProgress(
            stage_label="Act 1",
            checkpoints=[
                Checkpoint(id="cp-1", title="Start", dm_notes="Begin", status="completed"),
                Checkpoint(id="cp-2", title="End", dm_notes="Finish", status="active"),
            ],
            guidance="Mid-play notes",
        ),
    )

    result = copy_campaign("source", character_id="rogue", name="Test Arc (Rogue)")

    new_id = result["campaign_id"]
    camp = journal_storage.get_campaign(new_id)
    assert camp is not None
    assert camp["name"] == "Test Arc (Rogue)"
    assert camp["character_ids"] == ["rogue"]
    assert camp["story_arc"] == "Premise."
    assert camp["copied_from"] == "source"
    assert journal_storage.get_campaign_npc(new_id, "guide")["body"] == "Helpful NPC."

    adventures = storage.list_adventures_for_campaign(new_id)
    assert len(adventures) == 2
    assert adventures[0]["status"] == "active"
    assert adventures[1]["status"] == "planned"

    first = storage.get_adventure(adventures[0]["id"])
    assert first is not None
    assert first["character_id"] == "rogue"
    assert "Old play history" not in first["log"]
    assert not first["summary"].strip()

    progress = load_story_progress(adventures[0]["id"])
    assert progress is not None
    assert progress.guidance == ""
    assert progress.checkpoints[0].status == "active"
    assert progress.checkpoints[1].status == "pending"
