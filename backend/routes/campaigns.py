"""Campaign journal API — campaigns, NPCs, locations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.dm.world_context import world_context_for_campaign
from backend.journal_storage import (
    delete_campaign,
    delete_campaign_location,
    delete_campaign_npc,
    get_campaign,
    get_campaign_location,
    get_campaign_npc,
    list_campaigns,
    save_campaign,
    save_campaign_location,
    save_campaign_npc,
)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignBody(BaseModel):
    name: str
    story_arc: str = ""
    status: str = "active"
    character_ids: list[str] = []


class CampaignUpdateBody(BaseModel):
    name: str | None = None
    story_arc: str | None = None
    status: str | None = None
    character_ids: list[str] | None = None


class JournalEntryBody(BaseModel):
    name: str
    body: str = ""


@router.get("")
def list_all():
    return {"campaigns": list_campaigns()}


@router.post("")
def create(body: CampaignBody):
    cid = save_campaign(None, body.model_dump())
    return {"id": cid, "campaign": get_campaign(cid)}


@router.get("/{campaign_id}")
def get_one(campaign_id: str):
    camp = get_campaign(campaign_id)
    if not camp:
        raise HTTPException(404, "Campaign not found")
    return {"campaign": camp}


@router.put("/{campaign_id}")
def update(campaign_id: str, body: CampaignUpdateBody):
    camp = get_campaign(campaign_id)
    if not camp:
        raise HTTPException(404, "Campaign not found")
    updates = body.model_dump(exclude_none=True)
    camp.update(updates)
    save_campaign(campaign_id, camp)
    return {"campaign": get_campaign(campaign_id)}


@router.delete("/{campaign_id}")
def remove(campaign_id: str):
    if not delete_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    return {"ok": True}


@router.get("/{campaign_id}/world-context")
def world_context(campaign_id: str):
    text = world_context_for_campaign(campaign_id)
    return {"campaign_id": campaign_id, "context": text}


# --- NPCs ---


@router.post("/{campaign_id}/npcs")
def create_npc(campaign_id: str, body: JournalEntryBody):
    if not get_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    npc_id = save_campaign_npc(campaign_id, None, body.model_dump())
    return {"id": npc_id, "npc": get_campaign_npc(campaign_id, npc_id)}


@router.get("/{campaign_id}/npcs/{npc_id}")
def get_npc(campaign_id: str, npc_id: str):
    npc = get_campaign_npc(campaign_id, npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    return {"npc": npc}


@router.put("/{campaign_id}/npcs/{npc_id}")
def update_npc(campaign_id: str, npc_id: str, body: JournalEntryBody):
    if not get_campaign_npc(campaign_id, npc_id):
        raise HTTPException(404, "NPC not found")
    save_campaign_npc(campaign_id, npc_id, body.model_dump())
    return {"npc": get_campaign_npc(campaign_id, npc_id)}


@router.delete("/{campaign_id}/npcs/{npc_id}")
def remove_npc(campaign_id: str, npc_id: str):
    if not delete_campaign_npc(campaign_id, npc_id):
        raise HTTPException(404, "NPC not found")
    return {"ok": True}


# --- Locations ---


@router.post("/{campaign_id}/locations")
def create_location(campaign_id: str, body: JournalEntryBody):
    if not get_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    loc_id = save_campaign_location(campaign_id, None, body.model_dump())
    return {"id": loc_id, "location": get_campaign_location(campaign_id, loc_id)}


@router.get("/{campaign_id}/locations/{location_id}")
def get_location(campaign_id: str, location_id: str):
    loc = get_campaign_location(campaign_id, location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    return {"location": loc}


@router.put("/{campaign_id}/locations/{location_id}")
def update_location(campaign_id: str, location_id: str, body: JournalEntryBody):
    if not get_campaign_location(campaign_id, location_id):
        raise HTTPException(404, "Location not found")
    save_campaign_location(campaign_id, location_id, body.model_dump())
    return {"location": get_campaign_location(campaign_id, location_id)}


@router.delete("/{campaign_id}/locations/{location_id}")
def remove_location(campaign_id: str, location_id: str):
    if not delete_campaign_location(campaign_id, location_id):
        raise HTTPException(404, "Location not found")
    return {"ok": True}
