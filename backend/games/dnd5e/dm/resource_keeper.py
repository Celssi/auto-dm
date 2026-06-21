"""Auto-update spell slots, concentration, Wild Shape, and short rest after each play turn."""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.games.dnd5e.characters.character_builder import apply_short_rest
from backend.games.dnd5e.characters.entity import (
    Dnd5eCharacter,
    character_from_dict,
    format_for_prompt,
)
from backend.games.dnd5e.characters.spell_resources import (
    apply_resource_updates,
    compute_wild_shape_max,
)
from backend.llm import get_langchain_chat_llm

_SHORT_REST_TRIGGERS = (
    "short rest",
    "short-rest",
    "brief rest",
    "take an hour to rest",
    "hour of rest",
    "hour to rest",
    "lyhyt lepo",
    "tunnin lepo",
)


class SpellCast(BaseModel):
    spell_name: str
    slot_level: int = Field(default=0, description="0 = default spell level; higher = upcast")
    ritual: bool = Field(default=False, description="Ritual cast — no slot spent")


class ResourceTurnUpdates(BaseModel):
    casts: list[SpellCast] = Field(default_factory=list)
    end_concentration: bool = Field(default=False)
    new_concentration: str = Field(
        default="", description="Spell name if concentrating, else empty"
    )
    wild_shape_used: bool = Field(default=False)
    short_rest: bool = Field(
        default=False, description="Character clearly finished a short rest this turn"
    )
    spend_hit_dice: int = Field(
        default=0, ge=0, le=20, description="Hit Dice spent during short rest, if stated"
    )


def narrative_short_rest_detected(user_message: str, dm_response: str) -> bool:
    combined = f"{user_message}\n{dm_response}".lower()
    if "long rest" in combined or "long-rest" in combined:
        return False
    return any(trigger in combined for trigger in _SHORT_REST_TRIGGERS)


def parse_hit_dice_to_spend(user_message: str, dm_response: str) -> int:
    text = f"{user_message}\n{dm_response}"
    for pattern in (
        r"spend\s+(\d+)\s+hit\s+dice",
        r"spend\s+(\d+)\s+hit\s+die",
        r"uses?\s+(\d+)\s+hit\s+dice",
        r"(\d+)\s+hit\s+dice\s+spent",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return max(0, int(match.group(1)))
    return 0


def _apply_short_rest_updates(
    char: Dnd5eCharacter, *, dice_to_spend: int
) -> tuple[dict, list[str]]:
    rest = apply_short_rest(char, dice_to_spend=dice_to_spend)
    entity = dict(rest.get("entity_updates") or {})
    summary = str(rest.get("summary") or "Short rest.")
    if not entity:
        return {}, [summary]
    return entity, [summary]


def extract_resource_updates(
    *,
    char: Dnd5eCharacter,
    user_message: str,
    dm_response: str,
) -> ResourceTurnUpdates:
    ws_max = compute_wild_shape_max(char)
    prompt = f"""Analyze this D&D 5e solo play turn for RESOURCE changes only.

Character resources:
{format_for_prompt(char)[:3500]}

Rules:
- short_rest: true ONLY if the player or DM clearly completes a short rest (about 1 hour) this turn
  - spend_hit_dice: number of Hit Dice clearly spent for healing during that rest (0 if none stated)
  - If short_rest is true, leave casts empty and other fields false/default
- casts: ONLY when the player or DM clearly casts a leveled spell
  or cantrip this turn (not during a rest)
  - ritual=true only if explicitly a ritual cast (10+ min, no slot)
  - slot_level: set only for upcasting
    (e.g. Healing Word at 2nd level -> slot_level=2)
  - Cantrips: include in casts but they never spend slots
- new_concentration: spell name if a concentration spell begins; empty otherwise
- end_concentration: true only if concentration clearly ended
  (new conc spell, dropped, incapacitated)
- wild_shape_used: true only if Wild Shape was activated this turn\
{f" (max {ws_max} uses/long rest)" if ws_max else ""}
- Do NOT guess. Prefer empty lists/false over speculation.
- Long rest is handled elsewhere — do not set short_rest for a long rest.

Player: {user_message[:1500]}

DM response: {dm_response[:1500]}
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(ResourceTurnUpdates)
    return llm.invoke([HumanMessage(content=prompt)])


def run_resource_keeper(
    *,
    character: dict,
    user_message: str,
    dm_response: str,
) -> tuple[dict, list[str]]:
    if not dm_response.strip():
        return {}, []
    char = character_from_dict(character)

    if narrative_short_rest_detected(user_message, dm_response):
        dice = parse_hit_dice_to_spend(user_message, dm_response)
        return _apply_short_rest_updates(char, dice_to_spend=dice)

    updates = extract_resource_updates(
        char=char, user_message=user_message, dm_response=dm_response
    )
    if updates.short_rest:
        return _apply_short_rest_updates(char, dice_to_spend=updates.spend_hit_dice)

    entity_updates, logs = apply_resource_updates(char, updates)
    if not entity_updates and not logs:
        return {}, []
    return entity_updates, logs


def apply_cast_spell_shortcut(
    character: dict,
    spell_name: str,
    *,
    slot_level: int = 0,
    ritual: bool = False,
    audit_source: str = "shortcut",
) -> tuple[dict, list[str]]:
    """Deterministic spell cast without LLM (shortcut)."""
    char = character_from_dict(character)
    from backend.games.dnd5e.characters.spell_resources import apply_spell_cast

    ok, msg = apply_spell_cast(
        char,
        spell_name,
        slot_level=slot_level,
        ritual=ritual,
        audit_source=audit_source,
        inferred=False,
    )
    entity = {
        "spell_slots": dict(char.spell_slots),
        "concentration": char.concentration,
        "wild_shape_uses": char.wild_shape_uses,
    }
    return entity, [msg if ok else f"⚠ {msg}"]
