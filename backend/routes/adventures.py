"""Adventure API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.dm.campaign_bootstrap import flesh_out_planned_adventure, generate_adventure_outline
from backend.dm.story_director import (
    ensure_story_progress,
    find_next_planned_adventure,
    load_story_progress,
    player_progress_view,
    reset_story_progress,
)
from backend.journal_storage import get_campaign
from backend.storage import (
    create_session,
    delete_adventure,
    find_session_for_adventure,
    get_adventure,
    get_character,
    list_adventures,
    save_adventure,
)

router = APIRouter(prefix="/api/adventures", tags=["adventures"])


def _adventure_for_player(adv: dict[str, Any]) -> dict[str, Any]:
    adv_id = str(adv.get("id") or "")
    # Never run LLM work on read — progress is created at begin/bootstrap/outline time.
    progress = load_story_progress(adv_id)
    safe = {k: v for k, v in adv.items() if k not in ("outline", "summary")}
    safe["player_progress"] = player_progress_view(progress)
    return safe


class AdventureCreateBody(BaseModel):
    name: str
    mode: str = "freeform"
    theme: str = ""
    character_id: str = ""
    campaign_id: str = ""
    include_faerun: bool = False
    outline: str = ""


class AdventureUpdateBody(BaseModel):
    meta: dict[str, Any]
    outline: str = ""


@router.get("")
def list_all(campaign_id: str | None = Query(default=None)):
    return {"adventures": list_adventures(campaign_id=campaign_id or None)}


@router.get("/{adv_id}")
def get_one(adv_id: str):
    adv = get_adventure(adv_id)
    if not adv:
        raise HTTPException(404, "Adventure not found")
    return {"adventure": _adventure_for_player(adv)}


@router.post("")
def create(body: AdventureCreateBody):
    outline = body.outline
    if not outline and body.theme:
        outline = generate_adventure_outline(
            mode=body.mode,
            theme=body.theme,
            character_id=body.character_id,
            include_faerun=body.include_faerun,
            campaign_id=body.campaign_id,
        )
    meta = {
        "name": body.name,
        "mode": body.mode,
        "theme": body.theme,
        "character_id": body.character_id,
        "campaign_id": body.campaign_id,
        "include_faerun": body.include_faerun,
        "status": "active",
    }
    adv_id = save_adventure(None, meta, outline=outline)
    if outline:
        ensure_story_progress(adv_id, outline)
    adv = get_adventure(adv_id)
    return {"id": adv_id, "adventure": _adventure_for_player(adv or {})}


@router.put("/{adv_id}")
def update(adv_id: str, body: AdventureUpdateBody):
    adv = get_adventure(adv_id)
    if not adv:
        raise HTTPException(404, "Adventure not found")
    meta = {**adv, **body.meta, "id": adv_id}
    save_adventure(adv_id, meta, outline=body.outline or adv.get("outline", ""))
    updated = get_adventure(adv_id)
    return {"adventure": _adventure_for_player(updated or {})}


@router.post("/{adv_id}/generate-outline")
def regen_outline(adv_id: str, body: AdventureCreateBody):
    adv = get_adventure(adv_id)
    if not adv:
        raise HTTPException(404, "Adventure not found")
    outline = generate_adventure_outline(
        mode=body.mode or adv.get("mode", "freeform"),
        theme=body.theme or adv.get("theme", adv.get("name", "")),
        character_id=body.character_id or adv.get("character_id", ""),
        include_faerun=body.include_faerun or adv.get("include_faerun", False),
    )
    meta = {**adv, "outline": outline}
    save_adventure(adv_id, meta, outline=outline)
    reset_story_progress(adv_id)
    ensure_story_progress(adv_id, outline, force=True)
    updated = get_adventure(adv_id)
    return {"adventure": _adventure_for_player(updated or {})}


@router.post("/{adv_id}/complete")
def complete_adventure(adv_id: str):
    adv = get_adventure(adv_id)
    if not adv:
        raise HTTPException(404, "Adventure not found")
    if adv.get("status") == "completed":
        campaign_id = str(adv.get("campaign_id") or "")
        seq = adv.get("sequence")
        after = int(seq) if seq is not None else None
        next_adv = (
            find_next_planned_adventure(campaign_id, after_sequence=after) if campaign_id else None
        )
        progress = load_story_progress(adv_id)
        return {
            "adventure": _adventure_for_player(adv),
            "next_adventure": next_adv,
            "player_progress": player_progress_view(progress),
        }
    save_adventure(adv_id, {**adv, "status": "completed"})
    campaign_id = str(adv.get("campaign_id") or "")
    seq = adv.get("sequence")
    after = int(seq) if seq is not None else None
    next_adv = (
        find_next_planned_adventure(campaign_id, after_sequence=after) if campaign_id else None
    )
    updated = get_adventure(adv_id)
    progress = load_story_progress(adv_id)
    return {
        "adventure": _adventure_for_player(updated or {}),
        "next_adventure": next_adv,
        "player_progress": player_progress_view(progress),
    }


@router.delete("/{adv_id}")
def remove(adv_id: str):
    if not delete_adventure(adv_id):
        raise HTTPException(404, "Adventure not found")
    return {"ok": True}


@router.post("/{adv_id}/start-session")
def start_session(adv_id: str):
    adv = get_adventure(adv_id)
    if not adv:
        raise HTTPException(404, "Adventure not found")
    existing = find_session_for_adventure(adv_id)
    if existing:
        return {"session_id": existing["id"], "created": False}
    character_id = adv.get("character_id") or ""
    campaign_id = adv.get("campaign_id") or ""
    if not character_id and campaign_id:
        campaign = get_campaign(campaign_id)
        if campaign and campaign.get("character_ids"):
            character_id = campaign["character_ids"][0]
    if not character_id or not get_character(character_id):
        raise HTTPException(400, "Adventure has no linked character")

    if adv.get("status") == "planned" and campaign_id:
        try:
            result = flesh_out_planned_adventure(
                adventure_id=adv_id,
                campaign_id=campaign_id,
                character_id=character_id,
                mode=adv.get("mode", "freeform"),  # type: ignore[arg-type]
                theme=adv.get("theme") or adv.get("name", ""),
                include_faerun=bool(adv.get("include_faerun")),
            )
            return {"session_id": result["session_id"], "created": True, "activated": True}
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    session_id = create_session(
        character_id=character_id,
        adventure_id=adv_id,
        name=f"{adv.get('name', adv_id)} - play",
        include_faerun=bool(adv.get("include_faerun")),
    )
    return {"session_id": session_id, "created": True}
