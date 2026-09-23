"""Brambletrek-specific API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.games.brambletrek.characters.resource_creation import (
    apply_resource_draft,
    draw_character_resources,
    draw_resource_bonus,
    roll_legacy,
)
from backend.games.brambletrek.play_handlers import (
    apply_journey_event,
    character_header,
    discard_journey,
    dismiss_session_combat,
    dragonkeep_action,
    draw_character_table,
    draw_journey_item,
    finish_journey_day,
    get_dragonkeep_state,
    get_session_combat,
    init_dragonkeep_state,
    legacy_abilities_payload,
    pending_journey_payload,
    persist_character,
    resource_draft_state,
    session_combat_action,
    set_resource_draft,
    start_journey_combat,
)
from backend.games.brambletrek.rag_config import GAME_ID
from backend.play_tools import deck_remaining, draw_cards, reset_deck
from backend.storage import get_character, get_session

router = APIRouter(prefix="/api/brambletrek", tags=["brambletrek"])


class CharacterBody(BaseModel):
    character: dict[str, Any]


class TableDrawBody(BaseModel):
    table: str


class ResourceBonusBody(BaseModel):
    stat: str
    draft: dict[str, Any] | None = None


class ApplyResourcesBody(BaseModel):
    draft: dict[str, Any] | None = None


class JourneyApplyBody(BaseModel):
    event_index: int


class DragonkeepActionBody(BaseModel):
    action: str
    gem: str = ""
    event_index: int = -1


class CombatActionBody(BaseModel):
    action: str
    hand_index: int = -1


@router.get("/characters/{char_id}/header")
def header(char_id: str):
    if not get_character(char_id):
        raise HTTPException(404, "Character not found")
    return character_header(char_id)


@router.put("/characters/{char_id}")
def update_character(char_id: str, body: CharacterBody):
    if not get_character(char_id):
        raise HTTPException(404, "Character not found")
    entity = persist_character(char_id, body.character)
    return {"character": entity, "header": character_header(char_id)}


@router.post("/characters/{char_id}/draw-table")
def draw_table(char_id: str, body: TableDrawBody):
    if not get_character(char_id):
        raise HTTPException(404, "Character not found")
    try:
        return draw_character_table(char_id, body.table)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/characters/{char_id}/draw-resources")
def draw_resources(char_id: str, session_id: str = ""):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    try:
        result = draw_character_resources(
            game_id=GAME_ID,
            char_id=char_id,
            legacy_id=str(char.get("legacy") or ""),
        )
        if session_id:
            set_resource_draft(session_id, result["draft"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/reason-ending")
def reason_ending(reason_band: str):
    from backend.games.brambletrek.dm.curated import format_reason_ending

    return {"preview": format_reason_ending(reason_band) if reason_band else ""}


@router.get("/character-table-preview")
def character_table_preview(table: str, band: str, card: str = ""):
    from backend.games.brambletrek.dm.curated import format_character_table

    if table not in ("reason", "background", "trinket"):
        raise HTTPException(400, f"Unknown table: {table}")
    return {"preview": format_character_table(table, band, card=card) if band else ""}


@router.post("/characters/{char_id}/resource-bonus")
def resource_bonus(char_id: str, body: ResourceBonusBody, session_id: str = ""):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    draft = resource_draft_state(session_id) if session_id else body.draft
    if not draft:
        raise HTTPException(400, "No resource draft in progress")
    try:
        result = draw_resource_bonus(
            draft,
            body.stat,
            game_id=GAME_ID,
            char_id=char_id,
            legacy_id=str(char.get("legacy") or ""),
        )
        if session_id:
            set_resource_draft(session_id, result["draft"])
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/characters/{char_id}/apply-resources")
def apply_resources(char_id: str, body: ApplyResourcesBody | None = None, session_id: str = ""):
    from backend.games.brambletrek.characters.entity import character_from_dict, character_to_dict

    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    draft = resource_draft_state(session_id) if session_id else (body.draft if body else None)
    if not draft:
        raise HTTPException(400, "No resource draft in progress")
    try:
        obj = character_from_dict(char)
        apply_resource_draft(obj, draft)
        entity = persist_character(char_id, character_to_dict(obj))
        if session_id:
            set_resource_draft(session_id, None)
        return {"character": entity}
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/characters/{char_id}/roll-legacy")
def roll_legacy_route(char_id: str):
    if not get_character(char_id):
        raise HTTPException(404, "Character not found")
    try:
        return roll_legacy()
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/characters/{char_id}/legacy-abilities")
def legacy_abilities(char_id: str):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    used = char.get("legacy_abilities_used") or {}
    return {
        "abilities": legacy_abilities_payload(str(char.get("legacy") or ""), used),
    }


@router.get("/deck/{char_id}")
def deck_status(char_id: str):
    return {"remaining": deck_remaining(GAME_ID, char_id)}


@router.post("/deck/{char_id}/reset")
def deck_reset(char_id: str):
    return reset_deck(GAME_ID, char_id)


@router.post("/deck/{char_id}/draw")
def deck_draw(char_id: str, count: int = 1):
    return draw_cards(count=count, game_id=GAME_ID, char_id=char_id)


@router.get("/sessions/{session_id}/journey")
def get_journey(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    char_id = sess["character_id"]
    return {"pending_journey": pending_journey_payload(session_id, char_id)}


@router.post("/sessions/{session_id}/journey/apply")
def journey_apply(session_id: str, body: JourneyApplyBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return apply_journey_event(session_id, sess["character_id"], body.event_index)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/sessions/{session_id}/journey/draw-item")
def journey_draw_item(session_id: str, body: JourneyApplyBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return draw_journey_item(session_id, sess["character_id"], body.event_index)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/sessions/{session_id}/journey/start-combat")
def journey_start_combat(session_id: str, body: JourneyApplyBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return start_journey_combat(session_id, sess["character_id"], body.event_index)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/sessions/{session_id}/journey/finish-day")
def journey_finish(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return finish_journey_day(session_id, sess["character_id"])


@router.post("/sessions/{session_id}/journey/discard")
def journey_discard(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return discard_journey(session_id)


@router.get("/sessions/{session_id}/dragonkeep")
def get_dragonkeep(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return get_dragonkeep_state(session_id, sess["character_id"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/sessions/{session_id}/dragonkeep/init")
def dragonkeep_init(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return init_dragonkeep_state(session_id, sess["character_id"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/sessions/{session_id}/dragonkeep/action")
def dragonkeep_act(session_id: str, body: DragonkeepActionBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return dragonkeep_action(
            session_id,
            sess["character_id"],
            body.action,
            gem=body.gem,
            event_index=body.event_index,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/sessions/{session_id}/combat")
def get_combat(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return {"combat": get_session_combat(session_id)}


@router.post("/sessions/{session_id}/combat")
def combat_act(session_id: str, body: CombatActionBody):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    try:
        return session_combat_action(
            session_id,
            sess["character_id"],
            body.action,
            hand_index=body.hand_index,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/sessions/{session_id}/combat/dismiss")
def combat_dismiss(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return dismiss_session_combat(session_id)
