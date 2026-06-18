"""Planned encounters and live combat state."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from backend.config import SAVES_DIR

CombatantKind = Literal["player", "enemy", "ally"]
CombatStatus = Literal["active", "ended"]


class EncounterEnemySpec(BaseModel):
    monster_name: str = Field(description="Canonical Monster Manual name")
    count: int = Field(default=1, ge=1, le=12)
    label: str = Field(default="", description="Optional group label")


class EncounterSpec(BaseModel):
    id: str
    name: str
    trigger_beat: str = Field(
        default="", description="Story checkpoint title that triggers this encounter"
    )
    description: str = ""
    enemies: list[EncounterEnemySpec] = Field(default_factory=list)


class Combatant(BaseModel):
    id: str
    name: str
    kind: CombatantKind = "enemy"
    monster_name: str = ""
    initiative: int = 0
    hp: int = 0
    max_hp: int = 0
    ac: int = 10
    attack_bonus: int = 0
    damage: str = ""
    conditions: list[str] = Field(default_factory=list)


class CombatState(BaseModel):
    encounter_id: str
    encounter_name: str
    round: int = 1
    turn_index: int = 0
    order: list[str] = Field(default_factory=list)
    combatants: list[Combatant] = Field(default_factory=list)
    status: CombatStatus = "active"


def _encounters_path(adventure_id: str) -> Path:
    return SAVES_DIR / "adventures" / adventure_id / "encounters.json"


def _combat_path(session_id: str) -> Path:
    return SAVES_DIR / "sessions" / session_id / "combat.json"


def load_adventure_encounters(adventure_id: str) -> list[EncounterSpec]:
    path = _encounters_path(adventure_id)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "encounters" in data:
        items = data["encounters"]
    elif isinstance(data, list):
        items = data
    else:
        return []
    return [EncounterSpec.model_validate(item) for item in items]


def save_adventure_encounters(adventure_id: str, encounters: list[EncounterSpec]) -> None:
    path = _encounters_path(adventure_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"encounters": [e.model_dump() for e in encounters]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_combat_state(session_id: str) -> CombatState | None:
    path = _combat_path(session_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    state = CombatState.model_validate(data)
    if state.status != "active":
        return None
    return state


def save_combat_state(session_id: str, state: CombatState) -> None:
    path = _combat_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def clear_combat_state(session_id: str) -> None:
    path = _combat_path(session_id)
    if path.is_file():
        path.unlink()


def new_encounter_id(name: str) -> str:
    base = name.lower().replace(" ", "-")[:32] or "encounter"
    return f"{base}-{uuid.uuid4().hex[:6]}"


def combat_state_view(state: CombatState | None) -> dict:
    """JSON-safe combat snapshot for API/UI."""
    if not state:
        return {}
    current_id = state.order[state.turn_index] if state.order else ""
    return {
        "encounter_id": state.encounter_id,
        "encounter_name": state.encounter_name,
        "round": state.round,
        "turn_index": state.turn_index,
        "current_combatant_id": current_id,
        "order": state.order,
        "combatants": [c.model_dump() for c in state.combatants],
        "status": state.status,
    }
