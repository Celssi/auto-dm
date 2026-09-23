"""Brambletrek campaign and opening scene bootstrap."""

from __future__ import annotations

from typing import Any

from backend.dm.campaign_bootstrap import BootstrapMode

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.dm.prose_style import NARRATION_STYLE_RULES, sanitize_narration_dashes
from backend.dm.session_opening import attach_opening_to_session
from backend.dm.story_director import ensure_story_progress
from backend.dm.story_memory import generate_opening_summary
from backend.games.brambletrek.characters.entity import character_from_dict, format_for_prompt
from backend.games.brambletrek.dm.curated import adventure_meta, format_adventure_context
from backend.games.brambletrek.rag_config import get_all_factions
from backend.journal_storage import save_campaign, slugify
from backend.llm import get_langchain_chat_llm
from backend.rag.engine import query_rules
from backend.storage import create_session, get_character, save_adventure, write_adventure_summary


class BrambletrekOpeningPackage(BaseModel):
    opening_scene: str = Field(
        description=(
            "2-3 cozy paragraphs placing the Gnawborn in Hyhill or the active module. "
            "End with a gentle choice or prompt to draw journey cards. "
            "Never use em dashes or en dashes; use commas or periods."
        )
    )


def _brambletrek_outline(active_adventure: str, meta: dict[str, Any], theme: str) -> str:
    label = meta.get("label", "Hyhill solo") if meta else "Hyhill solo"
    syn = str(meta.get("synopsis", theme)).strip()
    acts = meta.get("acts") or []
    acts_block = (
        "\n".join(f"- {a}" for a in acts) if acts else "- Daily journey draws and cozy discoveries"
    )
    tips = meta.get("tips") or []
    tips_block = "\n".join(f"- {t}" for t in tips) if tips else ""
    return f"""# {label}

## Premise
{syn}

## How to play
- Draw four cards per in-game day (Journey day shortcut or adventure scene when a module is active).
- Resolve events in order; use combat and recovery shortcuts when needed.
- Track Health, Morale, and Supplies on the character sheet.

## Structure
{acts_block}

{f"## Facilitator tips{chr(10)}{tips_block}" if tips_block else ""}
"""


def generate_brambletrek_opening(char: dict, adv: dict | None = None) -> str:
    char_obj = character_from_dict(char)
    active = str(char_obj.active_adventure or "")
    if adv and adv.get("source_module"):
        active = str(adv.get("source_module") or active)
    meta = adventure_meta(active)
    label = meta.get("label", "Hyhill solo") if meta else "Hyhill solo"
    module_ctx = format_adventure_context(active) if active else format_adventure_context("")
    rag_q = (
        f"Brambletrek opening scene for {label}. "
        f"{meta.get('synopsis', '')} "
        "Village of Hyhill, Gnawborn mousefolk, cozy journaling solo RPG."
    )
    rag = query_rules(
        rag_q,
        game_id="brambletrek",
        factions=get_all_factions(),
        character=char,
        top_k=8,
    )
    llm = get_langchain_chat_llm("claude").with_structured_output(BrambletrekOpeningPackage)
    pkg = llm.invoke(
        [
            HumanMessage(
                content=f"""Write the opening scene for a Brambletrek solo journaling session.

Adventure module: {label}
{module_ctx}

Player Gnawborn:
{format_for_prompt(char_obj)}

Rules and module context (cite tone, not mechanics verbatim):
{rag.answer[:2500] if rag.answer else "(use cozy Hyhill village tone)"}

Guidelines:
- Brambletrek is cozy journaling, not a dungeon crawl.
- Drop the player into a sensory moment in Hyhill or the module setting.
- Mention their Reason or Background lightly if set on the sheet.
- End by inviting them to draw today's cards or explore.
- No D&D mechanics, no d20.

{NARRATION_STYLE_RULES}
"""
            ),
        ]
    )
    return sanitize_narration_dashes(pkg.opening_scene.strip())


def bootstrap_brambletrek_campaign(
    *,
    character_id: str,
    mode: BootstrapMode = "module",
    theme: str = "",
    include_faerun: bool = False,
    campaign_name: str = "",
) -> dict[str, Any]:
    del mode, include_faerun  # Brambletrek always uses book modules, not D&D bootstrap modes.
    char = get_character(character_id)
    if not char:
        raise ValueError(f"Character not found: {character_id}")
    active = str(char.get("active_adventure") or "")
    meta = adventure_meta(active)
    adv_label = meta.get("label", "Hyhill solo") if meta else "Hyhill solo"
    theme_text = theme.strip() or str(meta.get("synopsis", adv_label)).strip()
    gnawborn_name = str(char.get("name") or "Gnawborn").strip()
    camp_name = campaign_name.strip() or f"Brambletrek: {gnawborn_name}"
    campaign_id = slugify(camp_name)
    save_campaign(
        campaign_id,
        {
            "name": camp_name,
            "story_arc": format_adventure_context(active) or theme_text,
            "status": "active",
            "character_ids": [character_id],
            "game_id": "brambletrek",
        },
    )
    adventure_id = slugify(f"{adv_label}-{gnawborn_name}")
    outline = _brambletrek_outline(active, meta, theme_text)
    opening = generate_brambletrek_opening(char)
    save_adventure(
        adventure_id,
        {
            "name": adv_label,
            "mode": "module",
            "theme": theme_text,
            "character_id": character_id,
            "campaign_id": campaign_id,
            "status": "active",
            "game_id": "brambletrek",
            "source_module": active,
        },
        outline=outline,
        log=f"# Adventure log\n\n{opening}\n",
    )
    summary = generate_opening_summary(log=opening, opening_scene=opening, game_id="brambletrek")
    write_adventure_summary(adventure_id, summary)
    ensure_story_progress(adventure_id, outline)
    session_id = create_session(
        character_id=character_id,
        adventure_id=adventure_id,
        name=f"{adv_label} - session 1",
        include_faerun=False,
    )
    attach_opening_to_session(session_id=session_id, opening=opening)
    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "adventure_id": adventure_id,
        "opening_scene": opening,
        "counts": {"npcs": 0, "locations": 0},
    }
