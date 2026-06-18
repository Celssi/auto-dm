"""One-shot campaign bootstrap: campaign + adventure + journal + session + opening scene."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.characters.entity import character_from_dict, format_for_prompt
from backend.journal_storage import (
    save_campaign,
    save_campaign_location,
    save_campaign_npc,
    slugify,
)
from backend.dm.story_memory import generate_full_summary
from backend.llm import get_langchain_chat_llm
from backend.rag.engine import query_rules
from backend.rag.plugin import get_all_factions
from backend.settings_store import load_settings
from backend.storage import (
    create_session,
    get_character,
    save_adventure,
    save_session_messages,
    write_adventure_summary,
)

BootstrapMode = Literal["freeform", "module"]


class JournalEntrySpec(BaseModel):
    name: str = Field(description="Display name")
    body: str = Field(description="Description: appearance, personality, role, current status")


class CampaignBootstrapSpec(BaseModel):
    campaign_name: str
    story_arc: str = Field(description="Campaign overview, main arc, mysteries, factions")
    adventure_name: str
    adventure_outline: str = Field(description="Markdown outline with acts, encounters, endings")
    npcs: list[JournalEntrySpec] = Field(default_factory=list, description="3-8 key NPCs")
    locations: list[JournalEntrySpec] = Field(default_factory=list, description="3-6 key locations")
    opening_scene: str = Field(description="2-4 paragraphs of in-world DM narration to start play")


def rag_context_for_theme(
    *,
    mode: BootstrapMode,
    theme: str,
    include_faerun: bool,
) -> tuple[str, list[str]]:
    factions = get_all_factions() if include_faerun else ["player", "dm", "monsters"]
    rules_query = theme
    if mode == "module" and include_faerun:
        rules_query = f"Adventure in Faerûn: {theme}. Locations, NPCs, plot hooks."
        factions = ["adventures_faerun", "heroes_faerun", "dm"]
    elif mode == "module":
        rules_query = f"D&D adventure module: {theme}. Dungeons, encounters, plot."
        factions = ["dm", "adventures_faerun"]
    rag = query_rules(rules_query, factions=factions, top_k=8, use_rerank=True, generate_answer=False)
    context = "\n\n".join(
        f"{s.get('source_label', s.get('label', '?'))} p.{s.get('page', '?')}: {s.get('text', '')[:600]}"
        for s in rag.sources[:6]
    )
    return context, factions


def generate_bootstrap_spec(
    *,
    mode: BootstrapMode,
    theme: str,
    character_id: str,
    include_faerun: bool = False,
    campaign_name: str = "",
) -> CampaignBootstrapSpec:
    char = get_character(character_id)
    if not char:
        raise ValueError(f"Character not found: {character_id}")
    char_obj = character_from_dict(char)
    prefs = load_settings()
    include_faerun = include_faerun or prefs.get("include_faerun", False)
    context, _ = rag_context_for_theme(mode=mode, theme=theme, include_faerun=include_faerun)

    setting = "Faerûn (Forgotten Realms)" if include_faerun else "freeform/homebrew"
    name_hint = f'\nPreferred campaign name: "{campaign_name}".' if campaign_name.strip() else ""

    prompt = f"""Design a complete D&D 5e (2024) SOLO campaign package.

Mode: {mode}
Theme/hook: {theme}
Setting: {setting}
{name_hint}

Player character:
{format_for_prompt(char_obj)}

Rulebook reference (use for tone and facts when relevant):
{context[:4000]}

Requirements:
- story_arc: main plot, mysteries, factions, long-term hooks (300-800 words)
- adventure_outline: markdown with Premise, Act 1, Key conflicts, Possible endings
- npcs: 4-8 entries with rich ChatDM-style bodies (appearance, personality, motivations, role)
- locations: 3-6 entries with atmosphere, features, current state
- opening_scene: drop the player INTO the action; end with a clear choice; no meta commentary
- Names must be consistent across outline, NPCs, locations, and opening scene
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(CampaignBootstrapSpec)
    return llm.invoke([HumanMessage(content=prompt)])


def bootstrap_campaign(
    *,
    character_id: str,
    mode: BootstrapMode = "freeform",
    theme: str,
    include_faerun: bool = False,
    campaign_name: str = "",
) -> dict[str, Any]:
    if not theme.strip():
        raise ValueError("Theme is required")
    spec = generate_bootstrap_spec(
        mode=mode,
        theme=theme.strip(),
        character_id=character_id,
        include_faerun=include_faerun,
        campaign_name=campaign_name,
    )

    camp_name = campaign_name.strip() or spec.campaign_name
    campaign_id = slugify(camp_name)
    save_campaign(
        campaign_id,
        {
            "name": camp_name,
            "story_arc": spec.story_arc,
            "status": "active",
            "character_ids": [character_id],
        },
    )

    for npc in spec.npcs:
        save_campaign_npc(campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body})
    for loc in spec.locations:
        save_campaign_location(campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body})

    adventure_id = slugify(spec.adventure_name)
    save_adventure(
        adventure_id,
        {
            "name": spec.adventure_name,
            "mode": mode,
            "theme": theme.strip(),
            "character_id": character_id,
            "campaign_id": campaign_id,
            "include_faerun": include_faerun,
            "status": "active",
        },
        outline=spec.adventure_outline,
        log=f"# Adventure log\n\n_Bootstrap opening scene logged._\n\n{spec.opening_scene.strip()}\n",
    )

    npc_hints = "\n".join(f"- {n.name}: {n.body[:200]}" for n in spec.npcs[:8])
    summary = generate_full_summary(
        log=spec.opening_scene,
        outline=spec.adventure_outline,
        story_arc=spec.story_arc,
        npc_hints=npc_hints,
        opening_scene=spec.opening_scene,
    )
    write_adventure_summary(adventure_id, summary)

    session_id = create_session(
        character_id=character_id,
        adventure_id=adventure_id,
        name=f"{camp_name} — session 1",
        include_faerun=include_faerun,
    )
    opening = spec.opening_scene.strip()
    save_session_messages(
        session_id,
        [{"role": "assistant", "content": opening}],
    )

    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "adventure_id": adventure_id,
        "opening_scene": opening,
        "counts": {"npcs": len(spec.npcs), "locations": len(spec.locations)},
    }


def generate_adventure_outline(
    *,
    mode: str,
    theme: str,
    character_id: str,
    include_faerun: bool = False,
) -> str:
    """Legacy markdown-only outline for Adventures API."""
    spec = generate_bootstrap_spec(
        mode=mode if mode in ("freeform", "module") else "freeform",  # type: ignore[arg-type]
        theme=theme,
        character_id=character_id,
        include_faerun=include_faerun,
    )
    return spec.adventure_outline
