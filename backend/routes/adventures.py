"""Adventure API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.dm.campaign_bootstrap import generate_adventure_outline
from backend.storage import (
    create_session,
    delete_adventure,
    find_session_for_adventure,
    get_adventure,
    get_character,
    list_adventures,
    save_adventure,
)
from backend.journal_storage import get_campaign

router = APIRouter(prefix="/api/adventures", tags=["adventures"])


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
    return {"adventure": adv}


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
    return {"id": adv_id, "adventure": get_adventure(adv_id)}


@router.put("/{adv_id}")
def update(adv_id: str, body: AdventureUpdateBody):
    adv = get_adventure(adv_id)
    if not adv:
        raise HTTPException(404, "Adventure not found")
    meta = {**adv, **body.meta, "id": adv_id}
    save_adventure(adv_id, meta, outline=body.outline or adv.get("outline", ""))
    return {"adventure": get_adventure(adv_id)}


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
    return {"adventure": get_adventure(adv_id)}


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
    if not character_id:
        campaign_id = adv.get("campaign_id") or ""
        if campaign_id:
            campaign = get_campaign(campaign_id)
            if campaign and campaign.get("character_ids"):
                character_id = campaign["character_ids"][0]
    if not character_id or not get_character(character_id):
        raise HTTPException(400, "Adventure has no linked character")
    session_id = create_session(
        character_id=character_id,
        adventure_id=adv_id,
        name=f"{adv.get('name', adv_id)} - play",
        include_faerun=bool(adv.get("include_faerun")),
    )
    return {"session_id": session_id, "created": True}
