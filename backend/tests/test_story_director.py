"""Story Director checkpoint and spoiler-safe brief tests."""

import tempfile
from pathlib import Path

import backend.config as cfg
from backend.dm.story_director import (
    Checkpoint,
    StoryProgress,
    apply_completion_if_done,
    build_narrator_brief,
    find_next_planned_adventure,
    player_progress_view,
)
from backend.storage import save_adventure


def test_narrator_brief_hides_pending_beats():
    progress = StoryProgress(
        stage_label="Act 1",
        checkpoints=[
            Checkpoint(
                id="cp-1", title="Arrival", dm_notes="Reach the village.", status="completed"
            ),
            Checkpoint(
                id="cp-2", title="The secret", dm_notes="Find the hidden tomb.", status="active"
            ),
            Checkpoint(
                id="cp-3", title="Final confrontation", dm_notes="Boss fight.", status="pending"
            ),
        ],
    )
    brief = build_narrator_brief(progress)
    assert "Final confrontation" not in brief
    assert "Boss fight" not in brief
    assert "The secret" in brief
    assert "Find the hidden tomb" in brief
    assert "Arrival" in brief


def test_player_progress_only_shows_completed():
    progress = StoryProgress(
        stage_label="Act 2",
        checkpoints=[
            Checkpoint(id="cp-1", title="Done beat", dm_notes="x", status="completed"),
            Checkpoint(id="cp-2", title="Secret future", dm_notes="y", status="pending"),
        ],
    )
    view = player_progress_view(progress)
    assert view["completed_beats"] == ["Done beat"]
    assert "Secret future" not in str(view)


def test_find_next_planned_adventure_by_sequence():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.storage as storage

    storage.ADVENTURES_DIR = tmpdir / "adventures"
    storage.ADVENTURES_INDEX = storage.ADVENTURES_DIR / "index.json"
    storage.ADVENTURES_DIR.mkdir(parents=True, exist_ok=True)
    save_adventure(
        "adv-1",
        {"name": "First", "campaign_id": "camp-1", "status": "completed", "sequence": 1},
        outline="# First",
    )
    save_adventure(
        "adv-2",
        {"name": "Second", "campaign_id": "camp-1", "status": "planned", "sequence": 2},
        outline="# Second",
    )
    save_adventure(
        "adv-3",
        {"name": "Third", "campaign_id": "camp-1", "status": "planned", "sequence": 3},
        outline="# Third",
    )
    nxt = find_next_planned_adventure("camp-1", after_sequence=1)
    assert nxt is not None
    assert nxt["id"] == "adv-2"
    assert nxt["name"] == "Second"


def test_apply_completion_marks_adventure_and_finds_next():
    tmpdir = Path(tempfile.mkdtemp())
    cfg.SAVES_DIR = tmpdir
    import backend.storage as storage

    storage.ADVENTURES_DIR = tmpdir / "adventures"
    storage.ADVENTURES_INDEX = storage.ADVENTURES_DIR / "index.json"
    storage.ADVENTURES_DIR.mkdir(parents=True, exist_ok=True)
    save_adventure(
        "adv-done",
        {"name": "Done", "campaign_id": "camp-1", "status": "active", "sequence": 1},
        outline="# Done",
    )
    save_adventure(
        "adv-next",
        {"name": "Next", "campaign_id": "camp-1", "status": "planned", "sequence": 2},
        outline="# Next",
    )
    progress = StoryProgress(
        stage_label="Finale",
        checkpoints=[
            Checkpoint(id="cp-1", title="End", dm_notes="x", status="completed"),
        ],
    )
    result = apply_completion_if_done("adv-done", progress)
    assert result["adventure_complete"] is True
    assert result["next_adventure"]["id"] == "adv-next"
