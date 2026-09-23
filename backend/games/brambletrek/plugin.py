"""Brambletrek game plugin assembly."""

from __future__ import annotations

from backend.games.brambletrek import rag_config
from backend.games.brambletrek.actions import (
    match_brambletrek_shortcut,
    run_shortcut_for_plugin,
    shortcuts_list_for_character,
)
from backend.games.brambletrek.characters.character_builder import (
    character_creation_summary,
    finalize_new_character,
    rebuild_character,
)
from backend.games.brambletrek.characters.character_data import character_options_payload
from backend.games.brambletrek.characters.entity import (
    character_from_dict,
    character_to_dict,
    default_character,
    format_for_prompt,
)
from backend.games.brambletrek.dm.play_adapter import BRAMBLETREK_PLAY_ADAPTER
from backend.games.brambletrek.prompts import brambletrek_system_prompt
from backend.games.brambletrek.rag_config import get_all_factions, get_pdf_sources
from backend.games.brambletrek.rag_hooks import BRAMBLETREK_RAG_HOOKS
from backend.games.registry import GamePlugin


def _system_prompt(**kwargs) -> str:
    char = kwargs.get("character")
    story_mode = str(kwargs.get("story_mode") or "player")
    card_source = str(kwargs.get("card_source") or "virtual")
    return brambletrek_system_prompt(
        language_instruction="Respond in the same language the player uses.",
        character=char,
        story_mode=story_mode,
        card_source=card_source,
    )


def _match_shortcut(text: str) -> str | None:
    return match_brambletrek_shortcut(text)


def _shortcuts() -> list[dict[str, str]]:
    return shortcuts_list_for_character()


BRAMBLETREK_PLUGIN = GamePlugin(
    id=rag_config.GAME_ID,
    label="Brambletrek",
    collection_name=rag_config.COLLECTION,
    character_from_dict=character_from_dict,
    character_to_dict=character_to_dict,
    default_character=default_character,
    rebuild_character=rebuild_character,
    finalize_new_character=finalize_new_character,
    character_creation_summary=character_creation_summary,
    character_options_payload=character_options_payload,
    shortcuts=_shortcuts(),
    run_shortcut=run_shortcut_for_plugin,
    match_shortcut=_match_shortcut,
    system_prompt=_system_prompt,
    get_all_factions=get_all_factions,
    pdf_sources=get_pdf_sources(),
    format_character_for_prompt=format_for_prompt,
    rag=BRAMBLETREK_RAG_HOOKS,
    play=BRAMBLETREK_PLAY_ADAPTER,
)
