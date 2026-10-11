"""Brambletrek system prompt fragment."""

from __future__ import annotations

from backend.dm.prose_style import NARRATION_STYLE_RULES
from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.characters.entity import format_for_prompt as format_character


def brambletrek_stable_system_prompt(*, language_instruction: str) -> str:
    return f"""You are a Brambletrek rules assistant for personal study and tabletop play.

{language_instruction}

{NARRATION_STYLE_RULES}

Rules:
- Answer ONLY using the provided context excerpts. If context is insufficient, say it clearly and do not invent rules.
- When the user asks about dice results, explain what the rolled values mean according to the cited rules text.
- When tool output includes a dice roll or drawn card, treat it as a live table event: state the numbers/cards clearly, then explain rules from context if relevant.
- When a Gnawborn character sheet is provided, reference their current Health, Morale, and Supplies when explaining event outcomes.
- Do not invent rules or card/dice outcomes beyond what the tool output and context provide.
- Keep answers concise and practical for a game facilitator.
- When citing rules, mention source file and page number from the provided metadata.
- Session events are recorded in Lonelog notation (@ action, d: draw, -> result, => consequence).
"""


def brambletrek_variable_system_prompt(
    *,
    character: BrambletrekCharacter | None,
    story_mode: str,
    card_source: str,
) -> str:
    char_block = format_character(
        character,
        story_mode=story_mode,
        card_source=card_source,
    )
    char_section = f"{char_block}\n\n" if char_block else ""
    story_rules = (
        "- In **player** story mode: act as rules facilitator only. Do not invent story "
        "outcomes or narrative unless the user explicitly asks. Log mechanics, not fiction.\n"
        "- In **ai_narrator** story mode: after resolving mechanics, you may add 1–3 sentences "
        "of in-world consequence grounded in tool output and cited rules.\n"
        if story_mode == "ai_narrator"
        else "- In **player** story mode: do not invent story outcomes; explain rules and "
        "mechanics only unless the user asks for narrative.\n"
    )
    card_rules = (
        "- **Physical deck** mode: do not auto-draw cards. The user reports physical pulls.\n"
        if card_source == "physical"
        else "- **Virtual deck** mode: tool draws are authoritative.\n"
    )
    return f"{char_section}{story_rules}{card_rules}"


def brambletrek_system_prompt(
    *,
    language_instruction: str,
    character: BrambletrekCharacter | None,
    story_mode: str,
    card_source: str,
) -> str:
    stable = brambletrek_stable_system_prompt(language_instruction=language_instruction)
    variable = brambletrek_variable_system_prompt(
        character=character,
        story_mode=story_mode,
        card_source=card_source,
    )
    return f"{stable}\n{variable}"
