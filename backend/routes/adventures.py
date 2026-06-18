"""Adventure API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.dm.campaign_bootstrap import generate_adventure_outline
from backend.storage import delete_adventure, get_adventure, list_adventures, save_adventure

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
def list_all():
    return {"adventures": list_adventures()}


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
