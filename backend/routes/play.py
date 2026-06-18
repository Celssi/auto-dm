"""Play session bootstrap API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.dm.campaign_bootstrap import (
    bootstrap_adventure_for_campaign,
    bootstrap_campaign,
    generate_campaign_with_plan,
)

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
    theme: str = ""
    include_faerun: bool = False
    adventure_name: str = ""
    auto_continue: bool = False


class GenerateCampaignBody(BaseModel):
    character_id: str = ""
    mode: str = Field(default="freeform", pattern="^(freeform|module)$")
    theme: str
    adventure_count: int = Field(default=3, ge=1, le=8)
    include_faerun: bool = False
    campaign_name: str = ""
    bootstrap_first: bool = False


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
            auto_continue=body.auto_continue,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return result


@router.post("/generate-campaign")
def play_generate_campaign(body: GenerateCampaignBody):
    try:
        result = generate_campaign_with_plan(
            character_id=body.character_id,
            mode=body.mode,  # type: ignore[arg-type]
            theme=body.theme,
            adventure_count=body.adventure_count,
            include_faerun=body.include_faerun,
            campaign_name=body.campaign_name,
            bootstrap_first=body.bootstrap_first,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return result
