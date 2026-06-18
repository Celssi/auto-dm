"""D&D 5e system prompt builder."""

from __future__ import annotations

from backend.characters.entity import Dnd5eCharacter, format_for_prompt


def dnd5e_system_prompt(
    *,
    character: Dnd5eCharacter | None = None,
    adventure_outline: str = "",
    canon_summary: str = "",
    recent_scenes: str = "",
    world_context: str = "",
    include_faerun: bool = False,
) -> str:
    entity_block = format_for_prompt(character) if character else "No character loaded."
    extra = """You are the Dungeon Master for a D&D 5e (2024) solo session.
- Narrate in evocative third-person past tense.
- Offer meaningful choices; never decide for the player without their input.
- Use d20 tests with advantage/disadvantage for ability checks, saves, and attacks.
- Track HP, AC, spell slots, and conditions on the character sheet.
- Use the solo d6 oracle when an impartial yes/no is needed.
- When rules are unclear, state your ruling and cite PHB/DMG when possible.
- Respect **Established facts** in Adventure canon. Continue from **Current situation**.
- Do not contradict canon unless the player explicitly retcons.
- Do not use em dashes (—) or en dashes (–) in narration. Use commas, periods, or a plain hyphen for ranges.
"""
    if character:
        setting = (character.campaign_setting or "freeform").strip().lower()
        notes = (character.campaign_notes or "").strip()
        if setting == "faerun" or include_faerun:
            extra += "- Setting: Faerûn (Forgotten Realms). Use Heroes of Faerûn and Adventures in Faerûn.\n"
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
    if adventure_outline.strip():
        extra += f"\n## Adventure outline\n{adventure_outline.strip()[:4000]}\n"

    return f"""{extra}

## Character
{entity_block}
"""
