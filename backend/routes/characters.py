"""Character API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.characters.character_builder import (
    add_multiclass_level,
    character_creation_summary,
    finalize_new_character,
    level_up_preview,
    rebuild_character,
)
from backend.characters.character_data import character_options_payload, multiclass_prerequisites
from backend.characters.entity import character_from_dict, character_to_dict, default_character
from backend.dm.graph import level_up_character
from backend.settings_store import load_settings
from backend.storage import delete_character, get_character, list_characters, save_character

router = APIRouter(prefix="/api/characters", tags=["characters"])


class CharacterBody(BaseModel):
    character: dict[str, Any]


class LevelUpBody(BaseModel):
    hp_roll: int | None = None
    asi_choices: list[dict[str, Any]] | None = None
    class_name: str | None = None
    cantrips: list[str] | None = None
    prepared_spells: list[str] | None = None
    known_spells: list[str] | None = None


class MulticlassBody(BaseModel):
    class_name: str


@router.get("")
def list_all():
    return {"characters": list_characters()}


@router.get("/options")
def options(include_faerun: bool = False):
    prefs = load_settings()
    use_faerun = include_faerun or prefs.get("include_faerun", False)
    payload = character_options_payload(include_faerun=use_faerun)
    payload["multiclass_prerequisites"] = {
        cid: multiclass_prerequisites(cid) for cid in [c["id"] for c in payload.get("classes", [])]
    }
    return payload


@router.get("/{char_id}/summary")
def summary(char_id: str):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    obj = rebuild_character(character_from_dict(char))
    return {"summary": character_creation_summary(obj), "character": character_to_dict(obj)}


@router.get("/{char_id}")
def get_one(char_id: str):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    return {"character": char}


@router.post("")
def create(body: CharacterBody):
    data = body.character if body.character else {}
    char = finalize_new_character(character_from_dict(data) if data else default_character())
    char_id = save_character(None, character_to_dict(char))
    return {"id": char_id, "character": get_character(char_id)}


@router.put("/{char_id}")
def update(char_id: str, body: CharacterBody):
    char = rebuild_character(character_from_dict(body.character))
    save_character(char_id, character_to_dict(char))
    return {"character": get_character(char_id)}


@router.get("/{char_id}/level-up-preview")
def level_up_preview_route(char_id: str, class_name: str | None = None):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    obj = rebuild_character(character_from_dict(char))
    return {"preview": level_up_preview(obj, class_name=class_name)}


@router.post("/{char_id}/level-up")
def level_up_route(char_id: str, body: LevelUpBody):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    pending: dict[str, Any] = {}
    if body.asi_choices is not None:
        pending["asi_choices"] = body.asi_choices
    if body.cantrips is not None:
        pending["cantrips"] = body.cantrips
    if body.prepared_spells is not None:
        pending["prepared_spells"] = body.prepared_spells
    if body.known_spells is not None:
        pending["known_spells"] = body.known_spells
    if pending:
        char.update(pending)
        save_character(
            char_id,
            character_to_dict(rebuild_character(character_from_dict(char))),
        )
    try:
        return level_up_character(char_id, hp_roll=body.hp_roll, class_name=body.class_name)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{char_id}/multiclass")
def add_multiclass(char_id: str, body: MulticlassBody):
    char = get_character(char_id)
    if not char:
        raise HTTPException(404, "Character not found")
    obj = rebuild_character(character_from_dict(char))
    updated, err = add_multiclass_level(obj, body.class_name)
    if err:
        raise HTTPException(400, err)
    save_character(char_id, character_to_dict(updated))
    return {
        "character": get_character(char_id),
        "summary": character_creation_summary(updated),
    }


@router.delete("/{char_id}")
def remove(char_id: str):
    if not delete_character(char_id):
        raise HTTPException(404, "Character not found")
    return {"ok": True}
