"""Story Director: hidden checkpoint progress for spoiler-free solo play."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.config import SAVES_DIR
from backend.llm import get_langchain_chat_llm
from backend.storage import get_adventure, list_adventures_for_campaign, save_adventure

CheckpointStatus = Literal["pending", "active", "completed", "skipped"]


class Checkpoint(BaseModel):
    id: str
    title: str = Field(description="Short beat name")
    dm_notes: str = Field(description="DM-only: goals, NPCs, twists for this beat")
    status: CheckpointStatus = "pending"


class StoryProgress(BaseModel):
    stage_label: str = Field(default="", description="e.g. Act 1, Climax")
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    guidance: str = Field(default="", description="DM-only notes for the current scene")


class OutlineCheckpoints(BaseModel):
    stage_label: str = Field(default="Act 1")
    checkpoints: list[dict[str, str]] = Field(
        description="List of {title, dm_notes} in story order. 4-10 beats.",
    )


class ProgressTurnUpdate(BaseModel):
    completed_checkpoint_ids: list[str] = Field(
        default_factory=list,
        description="IDs of checkpoints fully resolved this turn",
    )
    activate_checkpoint_id: str = Field(
        default="",
        description="ID of checkpoint to mark active next, if advancing",
    )
    guidance: str = Field(
        default="",
        description="Updated DM guidance for the next scene (1-3 sentences)",
    )
    stage_label: str = Field(
        default="", description="Update act label if the story moved to a new act"
    )


def _progress_path(adventure_id: str) -> Path:
    return SAVES_DIR / "adventures" / adventure_id / "progress.json"


def load_story_progress(adventure_id: str) -> StoryProgress | None:
    path = _progress_path(adventure_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return StoryProgress.model_validate(data)


def save_story_progress(adventure_id: str, progress: StoryProgress) -> None:
    path = _progress_path(adventure_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(progress.model_dump_json(indent=2), encoding="utf-8")


def parse_outline_to_progress(outline: str) -> StoryProgress:
    llm = get_langchain_chat_llm("claude").with_structured_output(OutlineCheckpoints)
    prompt = f"""Break this D&D adventure outline into ordered story checkpoints for a solo DM.

Each checkpoint is one dramatic beat the player can discover through play.
- title: short player-facing name (no spoilers in titles for future beats)
- dm_notes: DM-only detail (NPCs, locations, secrets, possible endings for THIS beat only)

Use 4-10 checkpoints covering premise through resolution.

Outline:
{outline[:8000]}
"""
    spec = llm.invoke([HumanMessage(content=prompt)])
    checkpoints: list[Checkpoint] = []
    for i, cp in enumerate(spec.checkpoints, start=1):
        checkpoints.append(
            Checkpoint(
                id=f"cp-{i}",
                title=str(cp.get("title") or f"Beat {i}").strip(),
                dm_notes=str(cp.get("dm_notes") or cp.get("notes") or "").strip(),
                status="active" if i == 1 else "pending",
            )
        )
    return StoryProgress(stage_label=spec.stage_label or "Act 1", checkpoints=checkpoints)


def reset_story_progress(adventure_id: str) -> None:
    path = _progress_path(adventure_id)
    if path.is_file():
        path.unlink()


def ensure_story_progress(
    adventure_id: str, outline: str, *, force: bool = False
) -> StoryProgress | None:
    outline = (outline or "").strip()
    if not outline:
        return load_story_progress(adventure_id)
    if force:
        reset_story_progress(adventure_id)
    existing = load_story_progress(adventure_id)
    if existing and existing.checkpoints:
        return existing
    progress = parse_outline_to_progress(outline)
    save_story_progress(adventure_id, progress)
    return progress


def find_next_planned_adventure(
    campaign_id: str,
    *,
    after_sequence: int | None = None,
) -> dict[str, Any] | None:
    planned = [a for a in list_adventures_for_campaign(campaign_id) if a.get("status") == "planned"]
    if after_sequence is not None:
        planned = [a for a in planned if int(a.get("sequence") or 0) > after_sequence]
    if not planned:
        return None
    planned.sort(key=lambda a: int(a.get("sequence") or 0))
    nxt = planned[0]
    adv_id = str(nxt.get("id") or "")
    if not adv_id:
        return None
    return {"id": adv_id, "name": str(nxt.get("name") or adv_id)}


def apply_completion_if_done(adventure_id: str, progress: StoryProgress) -> dict[str, Any]:
    """Mark adventure completed and find next planned adventure when all beats are done."""
    view = player_progress_view(progress)
    if not view.get("adventure_complete"):
        return {
            "adventure_complete": False,
            "next_adventure": None,
            "player_progress": view,
        }
    adv = get_adventure(adventure_id)
    if not adv:
        return {"adventure_complete": True, "next_adventure": None, "player_progress": view}
    if adv.get("status") != "completed":
        save_adventure(adventure_id, {**adv, "status": "completed"})
    campaign_id = str(adv.get("campaign_id") or "")
    next_adv = None
    if campaign_id:
        seq = adv.get("sequence")
        after = int(seq) if seq is not None else None
        next_adv = find_next_planned_adventure(campaign_id, after_sequence=after)
    return {
        "adventure_complete": True,
        "next_adventure": next_adv,
        "player_progress": view,
    }


def build_narrator_brief(progress: StoryProgress) -> str:
    if not progress.checkpoints:
        return ""
    active = next((c for c in progress.checkpoints if c.status == "active"), None)
    completed = [c for c in progress.checkpoints if c.status == "completed"]
    pending_count = sum(1 for c in progress.checkpoints if c.status == "pending")

    lines = [
        "## Story guide (DM only — never reveal future beats to the player)",
        f"Stage: {progress.stage_label or 'In progress'}",
    ]
    if completed:
        lines.append("Completed beats (player knows these):")
        for c in completed:
            lines.append(f"- {c.title}")
    if active:
        lines.append(f"\nCurrent beat: {active.title}")
        lines.append(f"Beat guidance:\n{active.dm_notes}")
    else:
        lines.append("\nNo active beat — infer next step from player action and completed beats.")
    if progress.guidance.strip():
        lines.append(f"\nScene guidance:\n{progress.guidance.strip()}")
    if pending_count:
        lines.append(
            f"\n{pending_count} beat(s) remain. Do not mention or foreshadow them. "
            "Let the player discover the story through play."
        )
    lines.append(
        "\nAdapt to player choices. Advance when the current beat's goals are met. "
        "Offer meaningful choices; do not railroad."
    )
    return "\n".join(lines)


def update_progress_after_turn(
    progress: StoryProgress,
    *,
    user_message: str,
    dm_response: str,
    log_entry: str = "",
) -> StoryProgress:
    if not progress.checkpoints:
        return progress

    active = next((c for c in progress.checkpoints if c.status == "active"), None)
    checkpoint_summary = "\n".join(
        f"- {c.id} [{c.status}] {c.title}: {c.dm_notes[:200]}" for c in progress.checkpoints
    )
    llm = get_langchain_chat_llm("claude").with_structured_output(ProgressTurnUpdate)
    prompt = f"""You track story checkpoint progress for a D&D solo adventure DM.

Review this play turn and update checkpoint status.

Rules:
- Mark a checkpoint completed only when its beat is clearly resolved in play
- activate_checkpoint_id: set the next pending checkpoint when moving forward (leave empty if staying on current beat)
- guidance: brief DM-only note for the NEXT scene (no future spoilers)
- stage_label: update only if the story clearly entered a new act

Checkpoints:
{checkpoint_summary}

Active beat: {active.title if active else "(none)"}

Player action:
{user_message[:1500]}

DM response:
{dm_response[:3500]}

Log entry:
{log_entry[:500] or "(none)"}
"""
    update = llm.invoke(
        [
            SystemMessage(content="Track adventure structure without spoiling the player."),
            HumanMessage(content=prompt),
        ]
    )

    checkpoints = [c.model_copy() for c in progress.checkpoints]
    by_id = {c.id: c for c in checkpoints}

    for cid in update.completed_checkpoint_ids:
        if cid in by_id and by_id[cid].status == "active":
            by_id[cid].status = "completed"

    if update.activate_checkpoint_id and update.activate_checkpoint_id in by_id:
        nxt = by_id[update.activate_checkpoint_id]
        if nxt.status == "pending":
            nxt.status = "active"

    if not any(c.status == "active" for c in checkpoints):
        for c in checkpoints:
            if c.status == "pending":
                c.status = "active"
                break

    return StoryProgress(
        stage_label=update.stage_label.strip() or progress.stage_label,
        checkpoints=checkpoints,
        guidance=update.guidance.strip() or progress.guidance,
    )


def player_progress_view(progress: StoryProgress | None) -> dict[str, Any]:
    """Spoiler-safe progress for the player UI."""
    if not progress or not progress.checkpoints:
        return {"stage": "", "completed_beats": [], "has_active_beat": False}
    completed = [c.title for c in progress.checkpoints if c.status == "completed"]
    has_active = any(c.status == "active" for c in progress.checkpoints)
    all_done = all(c.status in ("completed", "skipped") for c in progress.checkpoints)
    return {
        "stage": progress.stage_label if completed or has_active else "",
        "completed_beats": completed,
        "has_active_beat": has_active and not all_done,
        "adventure_complete": all_done and bool(completed),
    }
