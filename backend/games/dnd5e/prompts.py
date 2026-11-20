"""D&D 5e system prompt builder."""

from __future__ import annotations

from backend.dm.prose_style import NARRATION_STYLE_RULES
from backend.games.dnd5e.characters.entity import Dnd5eCharacter, format_for_prompt


def dnd5e_stable_system_prompt() -> str:
    return f"""You are the Dungeon Master for a D&D 5e (2024) solo session.
- Narrate in evocative third-person past tense.
- Offer meaningful choices; never decide for the player without their input.
- Use d20 tests with advantage/disadvantage for ability checks, saves, and attacks.
- Track HP, AC, spell slots, and conditions on the character sheet.
- The live ## Character block is authoritative for HP, AC, Hit Dice, slots, conditions, concentration, and Lay on Hands. Do not invent changes to those values.
- If Active effects lists a save DC, keep that DC. Do not pick a new DC for the same effect.
- Stay at the stated Current position. Do not teleport the PC back to an earlier spot unless they move there this turn.
- Do not portray deceased NPCs as alive. If Key NPCs lists someone under Deceased, they stay dead.
- Use the solo d6 oracle when an impartial yes/no is needed.
- This table uses D&D 5e (2024) only. Never apply 2014 rules, never offer a 2014 fallback, and never mix editions.
  Use 2024 Heroic Inspiration (spend to reroll one die), 2024 Exhaustion (-2 per level on d20 tests),
  one expended spell slot per turn, Weapon Mastery when the character has it,
  species (not race), and Origin feats from backgrounds.
- When rules are unclear, state a 2024 ruling and cite PHB/DMG 2024. Do not fall back to 2014.
- Respect **Established facts** in Adventure canon. Continue from **Current situation**.
- Do not contradict canon unless the player explicitly retcons.
- Follow the **Story guide** for structure, but let player choices shape how beats unfold.
- Never reveal or foreshadow story beats the player has not reached yet.

{NARRATION_STYLE_RULES}
"""


def dnd5e_variable_system_prompt(
    *,
    character: Dnd5eCharacter | None = None,
    story_brief: str = "",
    canon_summary: str = "",
    recent_scenes: str = "",
    world_context: str = "",
    include_faerun: bool = False,
) -> str:
    entity_block = format_for_prompt(character) if character else "No character loaded."
    extra = ""
    if character:
        setting = (character.campaign_setting or "freeform").strip().lower()
        notes = (character.campaign_notes or "").strip()
        if setting == "faerun" or include_faerun:
            extra += (
                "- Setting: Faerûn (Forgotten Realms). "
                "Use Heroes of Faerûn and Adventures in Faerûn.\n"
            )
        elif notes:
            extra += f"- Setting: {notes}\n"
        else:
            extra += "- Setting: freeform/homebrew unless the player specifies otherwise.\n"

    if canon_summary.strip():
        extra += f"\n## Adventure canon\n{canon_summary.strip()[:4000]}\n"
    if recent_scenes.strip():
        extra += f"\n## Recent scenes\n{recent_scenes.strip()[:3000]}\n"
    if world_context.strip():
        extra += f"\n{world_context.strip()[:6000]}\n"
    if story_brief.strip():
        extra += f"\n{story_brief.strip()[:5000]}\n"

    return f"""{extra}

## Character
{entity_block}
"""


def dnd5e_session_context(
    *,
    character: Dnd5eCharacter | None = None,
    story_brief: str = "",
    world_context: str = "",
    include_faerun: bool = False,
) -> str:
    """Slow-changing narrator context (setting, world bible, story brief): cacheable."""
    extra = ""
    if character:
        setting = (character.campaign_setting or "freeform").strip().lower()
        notes = (character.campaign_notes or "").strip()
        if setting == "faerun" or include_faerun:
            extra += (
                "- Setting: Faerûn (Forgotten Realms). "
                "Use Heroes of Faerûn and Adventures in Faerûn.\n"
            )
        elif notes:
            extra += f"- Setting: {notes}\n"
        else:
            extra += "- Setting: freeform/homebrew unless the player specifies otherwise.\n"
    if world_context.strip():
        extra += f"\n{world_context.strip()[:6000]}\n"
    if story_brief.strip():
        extra += f"\n{story_brief.strip()[:5000]}\n"
    return extra.strip()


def dnd5e_turn_context(
    *,
    character: Dnd5eCharacter | None = None,
    canon_summary: str = "",
    recent_scenes: str = "",
    scene_position: str = "",
) -> str:
    """Per-turn narrator context (canon, recent scenes, live sheet): sent after history."""
    entity_block = format_for_prompt(character) if character else "No character loaded."
    parts: list[str] = []
    if canon_summary.strip():
        parts.append(f"## Adventure canon\n{canon_summary.strip()[:4000]}")
    if recent_scenes.strip():
        parts.append(f"## Recent scenes\n{recent_scenes.strip()[:3000]}")
    if scene_position.strip():
        parts.append(
            "## Current position\n"
            f"{scene_position.strip()[:200]}\n"
            "Do not move the PC back to a previous location unless they go there this turn."
        )
    parts.append(
        "## Character\n"
        "Use these live values for HP, AC, Hit Dice, slots, conditions, concentration, and Lay on Hands. "
        "Ignore older numbers in the chat history. Do not invent resource changes.\n"
        f"{entity_block}"
    )
    return "\n\n".join(parts)


def dnd5e_system_prompt(
    *,
    character: Dnd5eCharacter | None = None,
    story_brief: str = "",
    canon_summary: str = "",
    recent_scenes: str = "",
    world_context: str = "",
    include_faerun: bool = False,
) -> str:
    stable = dnd5e_stable_system_prompt()
    variable = dnd5e_variable_system_prompt(
        character=character,
        story_brief=story_brief,
        canon_summary=canon_summary,
        recent_scenes=recent_scenes,
        world_context=world_context,
        include_faerun=include_faerun,
    )
    return f"{stable}\n{variable}"
