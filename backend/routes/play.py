"""Play session bootstrap API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.dm.campaign_bootstrap import bootstrap_adventure_for_campaign, bootstrap_campaign

router = APIRouter(prefix="/api/play", tags=["play"])


class BootstrapBody(BaseModel):
    character_id: str
    mode: str = Field(default="freeform", pattern="^(freeform|module)$")
    theme: str
    include_faerun: bool = False
    campaign_name: str = ""


class BootstrapAdventureBody(BaseModel):
    campaign_id: str
    character_id: str
    mode: str = Field(default="freeform", pattern="^(freeform|module)$")
    theme: str
    include_faerun: bool = False
    adventure_name: str = ""


@router.post("/bootstrap")
def play_bootstrap(body: BootstrapBody):
    try:
        result = bootstrap_campaign(
            character_id=body.character_id,
            mode=body.mode,  # type: ignore[arg-type]
            theme=body.theme,
            include_faerun=body.include_faerun,
            campaign_name=body.campaign_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return result


@router.post("/bootstrap-adventure")
def play_bootstrap_adventure(body: BootstrapAdventureBody):
    try:
        result = bootstrap_adventure_for_campaign(
            campaign_id=body.campaign_id,
            character_id=body.character_id,
            mode=body.mode,  # type: ignore[arg-type]
            theme=body.theme,
            include_faerun=body.include_faerun,
            adventure_name=body.adventure_name,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return result
