"""D&D 5e game plugin assembly."""

from __future__ import annotations

from backend.games.dnd5e import rag_config
from backend.games.dnd5e.actions import SHORTCUTS, match_dnd5e_shortcut, run_shortcut
from backend.games.dnd5e.characters.character_builder import (
    character_creation_summary,
    rebuild_character,
)
from backend.games.dnd5e.characters.character_data import character_options_payload
from backend.games.dnd5e.characters.entity import (
    character_from_dict,
    character_to_dict,
    default_character,
)
from backend.games.dnd5e.prompts import dnd5e_system_prompt
from backend.games.registry import GamePlugin
from backend.rag.plugin import get_all_factions, get_pdf_sources

DND5E_PLUGIN = GamePlugin(
    id=rag_config.GAME_ID,
    label="D&D 5e (2024)",
    collection_name=rag_config.COLLECTION,
    character_from_dict=character_from_dict,
    character_to_dict=character_to_dict,
    default_character=default_character,
    rebuild_character=rebuild_character,
    character_creation_summary=character_creation_summary,
    character_options_payload=character_options_payload,
    shortcuts=list(SHORTCUTS),
    run_shortcut=run_shortcut,
    match_shortcut=match_dnd5e_shortcut,
    system_prompt=dnd5e_system_prompt,
    get_all_factions=get_all_factions,
    pdf_sources=get_pdf_sources(),
)
