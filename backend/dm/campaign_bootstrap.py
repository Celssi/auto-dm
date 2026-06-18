"""One-shot campaign bootstrap: campaign + adventure + journal + session + opening scene."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.characters.entity import character_from_dict, format_for_prompt
from backend.dm.campaign_repair import (
    extract_encounters_from_outline,
    extract_journal_from_text,
    save_journal_entries,
)
from backend.dm.encounters import load_adventure_encounters, save_adventure_encounters
from backend.dm.session_opening import attach_opening_to_session
from backend.dm.story_director import ensure_story_progress
from backend.dm.story_memory import generate_opening_summary
from backend.dm.world_context import prior_adventures_context, world_context_for_campaign
from backend.journal_storage import (
    get_campaign,
    save_campaign,
    save_campaign_location,
    save_campaign_npc,
    slugify,
)
from backend.llm import get_langchain_chat_llm
from backend.rag.engine import query_rules
from backend.rag.plugin import get_all_factions
from backend.settings_store import load_settings
from backend.storage import (
    create_session,
    get_adventure,
    get_character,
    list_adventures,
    list_adventures_for_campaign,
    save_adventure,
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
    rag = query_rules(
        rules_query, factions=factions, top_k=8, use_rerank=True, generate_answer=False
    )
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
    summary = generate_opening_summary(
        log=spec.opening_scene,
        opening_scene=spec.opening_scene,
        npc_hints=npc_hints,
    )
    write_adventure_summary(adventure_id, summary)

    ensure_story_progress(adventure_id, spec.adventure_outline)
    encounters = extract_encounters_from_outline(spec.adventure_outline, spec.adventure_name)
    if encounters:
        save_adventure_encounters(adventure_id, encounters)

    session_id = create_session(
        character_id=character_id,
        adventure_id=adventure_id,
        name=f"{camp_name} - session 1",
        include_faerun=include_faerun,
    )
    opening = spec.opening_scene.strip()
    attach_opening_to_session(session_id=session_id, opening=opening)

    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "adventure_id": adventure_id,
        "opening_scene": opening,
        "counts": {"npcs": len(spec.npcs), "locations": len(spec.locations)},
    }


class AdventureContinuationSpec(BaseModel):
    adventure_name: str
    adventure_outline: str = Field(description="Markdown outline with acts, encounters, endings")
    opening_scene: str = Field(description="2-4 paragraphs continuing from prior adventures")
    new_npcs: list[JournalEntrySpec] = Field(
        default_factory=list, description="0-4 new or updated NPCs"
    )
    new_locations: list[JournalEntrySpec] = Field(
        default_factory=list,
        description="0-3 new or updated locations",
    )


def generate_adventure_spec_for_campaign(
    *,
    campaign_id: str,
    mode: BootstrapMode,
    theme: str,
    character_id: str,
    include_faerun: bool = False,
    adventure_name: str = "",
) -> AdventureContinuationSpec:
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")
    char = get_character(character_id)
    if not char:
        raise ValueError(f"Character not found: {character_id}")
    char_obj = character_from_dict(char)
    prefs = load_settings()
    include_faerun = include_faerun or prefs.get("include_faerun", False)
    context, _ = rag_context_for_theme(mode=mode, theme=theme, include_faerun=include_faerun)

    prior_adventures = list_adventures_for_campaign(campaign_id)
    prior_names = ", ".join(a.get("name", a["id"]) for a in prior_adventures) or "(none yet)"
    world = world_context_for_campaign(campaign_id, has_adventure_summary=True)
    prior_summaries = prior_adventures_context(campaign_id)
    name_hint = f'\nPreferred adventure name: "{adventure_name}".' if adventure_name.strip() else ""

    prompt = f"""Design the NEXT adventure in an ongoing D&D 5e (2024) SOLO campaign.

This is NOT a new campaign — continue from established canon. Do not reset or contradict prior events.

Campaign ID: {campaign_id}
Prior adventures: {prior_names}
New adventure theme/hook: {theme}
Mode: {mode}
{name_hint}

Player character:
{format_for_prompt(char_obj)}

Campaign world context (NPCs, locations, story arc — treat as canonical):
{world[:6000]}

Summaries of completed adventures in this campaign:
{prior_summaries[:5000] or "(first adventure in campaign — use campaign story arc only)"}

Rulebook reference:
{context[:3000]}

Requirements:
- adventure_outline: markdown with Premise, Act 1, Key conflicts, Possible endings
- opening_scene: drop the player INTO the new arc; reference prior events naturally; end with a clear choice
- new_npcs / new_locations: only entries that are NEW or materially changed; leave empty if none
- Names must be consistent with the campaign journal
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(AdventureContinuationSpec)
    try:
        return llm.invoke([HumanMessage(content=prompt)])
    except Exception:
        compact = f"""Design the NEXT adventure in an ongoing D&D 5e (2024) SOLO campaign.

Campaign: {campaign.get("name", campaign_id)}
Theme: {theme}
Adventure name hint: {adventure_name or "(choose a fitting title)"}
Mode: {mode}

Player character:
{format_for_prompt(char_obj)}

Campaign context (canonical):
{world[:3500]}

Prior adventure summaries:
{prior_summaries[:2500] or "(first adventure — use campaign story arc)"}

Return adventure_name, adventure_outline, opening_scene, and only new/changed NPCs and locations.
Keep opening_scene to 2-4 paragraphs."""
        return llm.invoke([HumanMessage(content=compact)])


class ModuleSourceSpec(BaseModel):
    title: str = Field(description="Published adventure or book title")
    source_label: str = Field(default="", description="Indexed PDF label from rulebooks")
    chapter: str = Field(default="", description="Chapter or section name, if applicable")
    pages: str = Field(default="", description="Page range, e.g. 12-45")
    notes: str = Field(default="", description="How this module fits the campaign arc")


class PlannedAdventureSpec(BaseModel):
    name: str
    theme: str = Field(description="One-line hook for this adventure")
    outline: str = Field(description="Markdown outline with Premise, Acts, Key conflicts, Endings")
    sequence: int = Field(description="Order in the campaign, starting at 1")
    source_module: ModuleSourceSpec | None = Field(
        default=None,
        description="Published module reference when mode is module",
    )


class CampaignPlanSpec(BaseModel):
    campaign_name: str
    story_arc: str = Field(
        description="Campaign overview, main arc, mysteries, factions, long-term hooks"
    )
    adventures: list[PlannedAdventureSpec] = Field(description="Ordered adventures in the campaign")
    npcs: list[JournalEntrySpec] = Field(default_factory=list, description="4-8 key recurring NPCs")
    locations: list[JournalEntrySpec] = Field(default_factory=list, description="3-6 key locations")
    source_module: ModuleSourceSpec | None = Field(
        default=None,
        description="Primary published source when basing the campaign on a book",
    )


class NextAdventureHookSpec(BaseModel):
    theme: str = Field(description="One or two sentences: what happens next in the campaign")
    adventure_name: str = Field(description="Evocative title for the next adventure")


def _module_source_dict(spec: ModuleSourceSpec | None) -> dict[str, str] | None:
    if not spec or not spec.title.strip():
        return None
    return {k: v for k, v in spec.model_dump().items() if str(v).strip()}


def generate_campaign_plan(
    *,
    mode: BootstrapMode,
    theme: str,
    character_id: str = "",
    adventure_count: int = 3,
    include_faerun: bool = False,
    campaign_name: str = "",
) -> tuple[CampaignPlanSpec, list[dict]]:
    prefs = load_settings()
    include_faerun = include_faerun or prefs.get("include_faerun", False)
    count = max(1, min(adventure_count, 8))

    if character_id.strip():
        char = get_character(character_id)
        if not char:
            raise ValueError(f"Character not found: {character_id}")
        char_section = format_for_prompt(character_from_dict(char))
    else:
        char_section = (
            "A solo adventurer (no specific character chosen yet). "
            "Design for a single 2024-rules hero without assuming class, race, or backstory."
        )

    rag = query_rules(
        theme if mode == "module" else f"D&D campaign arc: {theme}",
        factions=get_all_factions() if include_faerun else ["player", "dm", "monsters"],
        top_k=10 if mode == "module" else 6,
        use_rerank=True,
        generate_answer=False,
    )
    context = "\n\n".join(
        f"{s.get('source_label', s.get('label', '?'))} p.{s.get('page', '?')}: {s.get('text', '')[:700]}"
        for s in rag.sources[:8]
    )

    setting = "Faerûn (Forgotten Realms)" if include_faerun else "freeform/homebrew"
    name_hint = f'\nPreferred campaign name: "{campaign_name}".' if campaign_name.strip() else ""
    module_hint = ""
    if mode == "module":
        module_hint = f"""
Mode is MODULE: base the campaign on published material matching "{theme}".
- Set source_module on the campaign and on each adventure with title, source_label, chapter, pages when known from references.
- Adapt book content for solo play; do not assume a full party.
- Split the book into exactly {count} playable adventures in sequence.
"""
    else:
        module_hint = f"""
Mode is FREEFORM: invent an original campaign arc and exactly {count} linked adventures.
- Leave source_module null on all entries.
"""

    prompt = f"""Design a complete D&D 5e (2024) SOLO campaign PLAN (story arc + multiple adventures).

Theme/hook: {theme}
Setting: {setting}
Adventure count: {count}
{name_hint}
{module_hint}

Player character:
{char_section}

Rulebook reference (use for tone and facts when relevant):
{context[:5000]}

Requirements:
- story_arc: main plot, mysteries, factions, long-term hooks (400-900 words)
- adventures: exactly {count} entries, sequence 1..{count}, each with name, theme, and markdown outline
- Each outline: Premise, Act 1, Key conflicts, Possible endings (150-400 words each)
- Adventures must connect: later ones pay off threads from earlier ones
- npcs: 4-8 recurring entries with rich bodies (appearance, personality, motivations, role)
- locations: 3-6 entries with atmosphere, features, current state
- Names must be consistent across story_arc, adventures, NPCs, and locations
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(CampaignPlanSpec)
    spec = llm.invoke([HumanMessage(content=prompt)])
    if len(spec.adventures) > count:
        spec.adventures = spec.adventures[:count]
    return spec, rag.sources


def materialize_campaign_plan(
    *,
    spec: CampaignPlanSpec,
    character_id: str = "",
    mode: BootstrapMode,
    theme: str,
    include_faerun: bool = False,
    campaign_name: str = "",
    bootstrap_first: bool = False,
) -> dict[str, Any]:
    camp_name = campaign_name.strip() or spec.campaign_name
    campaign_id = slugify(camp_name)
    source = _module_source_dict(spec.source_module)
    char_ids = [character_id] if character_id.strip() else []

    save_campaign(
        campaign_id,
        {
            "name": camp_name,
            "story_arc": spec.story_arc,
            "status": "active",
            "character_ids": char_ids,
            "generation_mode": mode,
            "theme": theme.strip(),
            "adventure_count": len(spec.adventures),
            "source_module": source,
        },
    )

    for npc in spec.npcs:
        save_campaign_npc(campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body})
    for loc in spec.locations:
        save_campaign_location(campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body})

    if not spec.npcs or not spec.locations:
        extracted = extract_journal_from_text(
            spec.story_arc,
            [(a.name, a.outline) for a in sorted(spec.adventures, key=lambda a: a.sequence)],
        )
        if not spec.npcs:
            for npc in extracted.npcs:
                if npc.name.strip():
                    save_campaign_npc(
                        campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body}
                    )
        if not spec.locations:
            for loc in extracted.locations:
                if loc.name.strip():
                    save_campaign_location(
                        campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body}
                    )

    existing_ids = {a["id"] for a in list_adventures()}
    adventure_ids: list[str] = []
    sorted_advs = sorted(spec.adventures, key=lambda a: a.sequence)

    for i, adv in enumerate(sorted_advs):
        adv_id = slugify(adv.name)
        if adv_id in existing_ids:
            adv_id = f"{adv_id}-{len(existing_ids) + i + 1}"
        existing_ids.add(adv_id)
        status = "active" if i == 0 else "planned"
        save_adventure(
            adv_id,
            {
                "name": adv.name,
                "mode": mode,
                "theme": adv.theme,
                "character_id": character_id if character_id.strip() else "",
                "campaign_id": campaign_id,
                "include_faerun": include_faerun,
                "status": status,
                "sequence": adv.sequence,
                "source_module": _module_source_dict(adv.source_module),
            },
            outline=adv.outline,
            log=f"# Adventure log\n\n_Planned adventure {adv.sequence} in {camp_name}._\n",
        )
        encounters = extract_encounters_from_outline(adv.outline, adv.name)
        if encounters:
            save_adventure_encounters(adv_id, encounters)
        adventure_ids.append(adv_id)

    result: dict[str, Any] = {
        "campaign_id": campaign_id,
        "adventure_ids": adventure_ids,
        "counts": {
            "adventures": len(adventure_ids),
            "npcs": len(spec.npcs),
            "locations": len(spec.locations),
        },
    }

    if bootstrap_first and adventure_ids and character_id.strip():
        boot = flesh_out_planned_adventure(
            adventure_id=adventure_ids[0],
            campaign_id=campaign_id,
            character_id=character_id,
            mode=mode,
            theme=sorted_advs[0].theme,
            include_faerun=include_faerun,
        )
        result.update(boot)
    return result


def flesh_out_planned_adventure(
    *,
    adventure_id: str,
    campaign_id: str,
    character_id: str,
    mode: BootstrapMode,
    theme: str,
    include_faerun: bool = False,
) -> dict[str, Any]:
    """Add opening scene, summary, and session to a planned adventure."""
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")
    adv = get_adventure(adventure_id)
    if not adv:
        raise ValueError(f"Adventure not found: {adventure_id}")

    spec = generate_adventure_spec_for_campaign(
        campaign_id=campaign_id,
        mode=mode,
        theme=theme.strip(),
        character_id=character_id,
        include_faerun=include_faerun,
        adventure_name=adv.get("name", ""),
    )
    outline = (adv.get("outline") or "").strip() or spec.adventure_outline

    for npc in spec.new_npcs:
        save_campaign_npc(campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body})
    for loc in spec.new_locations:
        save_campaign_location(campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body})

    opening = spec.opening_scene.strip()
    save_adventure(
        adventure_id,
        {**adv, "status": "active"},
        outline=outline,
        log=f"# Adventure log\n\n{opening}\n",
    )

    summary = generate_opening_summary(
        log=opening,
        opening_scene=opening,
    )
    write_adventure_summary(adventure_id, summary)

    ensure_story_progress(adventure_id, outline)
    if not load_adventure_encounters(adventure_id):
        encounters = extract_encounters_from_outline(outline, adv.get("name", adventure_id))
        if encounters:
            save_adventure_encounters(adventure_id, encounters)

    adv_name = adv.get("name", adventure_id)
    session_id = create_session(
        character_id=character_id,
        adventure_id=adventure_id,
        name=f"{campaign.get('name', campaign_id)} - {adv_name}",
        include_faerun=include_faerun,
    )
    attach_opening_to_session(session_id=session_id, opening=opening)

    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "adventure_id": adventure_id,
        "opening_scene": opening,
        "counts": {"npcs": len(spec.new_npcs), "locations": len(spec.new_locations)},
    }


def generate_campaign_with_plan(
    *,
    character_id: str = "",
    mode: BootstrapMode = "freeform",
    theme: str,
    adventure_count: int = 3,
    include_faerun: bool = False,
    campaign_name: str = "",
    bootstrap_first: bool = False,
) -> dict[str, Any]:
    if not theme.strip():
        raise ValueError("Theme is required")
    spec, _ = generate_campaign_plan(
        mode=mode,
        theme=theme.strip(),
        character_id=character_id,
        adventure_count=adventure_count,
        include_faerun=include_faerun,
        campaign_name=campaign_name,
    )
    return materialize_campaign_plan(
        spec=spec,
        character_id=character_id,
        mode=mode,
        theme=theme.strip(),
        include_faerun=include_faerun,
        campaign_name=campaign_name,
        bootstrap_first=bootstrap_first,
    )


def suggest_next_adventure_hook(
    *,
    campaign_id: str,
    character_id: str,
) -> NextAdventureHookSpec:
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")
    char = get_character(character_id)
    if not char:
        raise ValueError(f"Character not found: {character_id}")
    char_obj = character_from_dict(char)

    prior_adventures = list_adventures_for_campaign(campaign_id)
    prior_names = ", ".join(a.get("name", a["id"]) for a in prior_adventures) or "(none yet)"
    world = world_context_for_campaign(campaign_id, has_adventure_summary=True)
    prior_summaries = prior_adventures_context(campaign_id)

    prompt = f"""You are planning the NEXT adventure in an ongoing D&D 5e (2024) SOLO campaign.

Campaign: {campaign.get("name", campaign_id)}
Prior adventures: {prior_names}

Player character:
{format_for_prompt(char_obj)}

Campaign world context:
{world[:6000]}

Summaries of prior adventures:
{prior_summaries[:5000] or "(first adventure — use story arc only)"}

Story arc:
{(campaign.get("story_arc") or "")[:4000]}

Propose what happens next. Do not repeat finished plots. Advance unresolved threads or introduce a natural escalation.
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(NextAdventureHookSpec)
    return llm.invoke([HumanMessage(content=prompt)])


def bootstrap_adventure_for_campaign(
    *,
    campaign_id: str,
    character_id: str,
    mode: BootstrapMode = "freeform",
    theme: str = "",
    include_faerun: bool = False,
    adventure_name: str = "",
    auto_continue: bool = False,
) -> dict[str, Any]:
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")

    resolved_theme = theme.strip()
    resolved_name = adventure_name.strip()
    if auto_continue or not resolved_theme:
        hook = suggest_next_adventure_hook(campaign_id=campaign_id, character_id=character_id)
        resolved_theme = hook.theme
        if not resolved_name:
            resolved_name = hook.adventure_name

    if not resolved_theme:
        raise ValueError("Theme is required")

    spec = generate_adventure_spec_for_campaign(
        campaign_id=campaign_id,
        mode=mode,
        theme=resolved_theme,
        character_id=character_id,
        include_faerun=include_faerun,
        adventure_name=resolved_name,
    )

    adv_name = resolved_name or spec.adventure_name
    adventure_id = slugify(adv_name)
    existing_ids = {a["id"] for a in list_adventures()}
    if adventure_id in existing_ids:
        adventure_id = f"{adventure_id}-{len(existing_ids) + 1}"

    prior_count = len(list_adventures_for_campaign(campaign_id))

    for npc in spec.new_npcs:
        save_campaign_npc(campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body})
    for loc in spec.new_locations:
        save_campaign_location(campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body})

    character_ids = list(campaign.get("character_ids") or [])
    if character_id not in character_ids:
        character_ids.append(character_id)
        save_campaign(campaign_id, {**campaign, "character_ids": character_ids})

    save_adventure(
        adventure_id,
        {
            "name": adv_name,
            "mode": mode,
            "theme": resolved_theme,
            "character_id": character_id,
            "campaign_id": campaign_id,
            "include_faerun": include_faerun,
            "status": "active",
            "sequence": prior_count + 1,
        },
        outline=spec.adventure_outline,
        log=f"# Adventure log\n\n_New adventure in {campaign.get('name', campaign_id)}._\n\n{spec.opening_scene.strip()}\n",
    )

    summary = generate_opening_summary(
        log=spec.opening_scene,
        opening_scene=spec.opening_scene,
    )
    write_adventure_summary(adventure_id, summary)

    ensure_story_progress(adventure_id, spec.adventure_outline)

    session_num = len(list_adventures_for_campaign(campaign_id))
    session_id = create_session(
        character_id=character_id,
        adventure_id=adventure_id,
        name=f"{campaign.get('name', campaign_id)} - {adv_name} (session {session_num})",
        include_faerun=include_faerun,
    )
    opening = spec.opening_scene.strip()
    attach_opening_to_session(session_id=session_id, opening=opening)

    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "adventure_id": adventure_id,
        "opening_scene": opening,
        "counts": {"npcs": len(spec.new_npcs), "locations": len(spec.new_locations)},
    }


def generate_adventure_outline(
    *,
    mode: str,
    theme: str,
    character_id: str,
    include_faerun: bool = False,
    campaign_id: str = "",
) -> str:
    """Markdown outline for Adventures API."""
    if campaign_id.strip():
        spec = generate_adventure_spec_for_campaign(
            campaign_id=campaign_id.strip(),
            mode=mode if mode in ("freeform", "module") else "freeform",  # type: ignore[arg-type]
            theme=theme,
            character_id=character_id,
            include_faerun=include_faerun,
        )
        return spec.adventure_outline
    spec = generate_bootstrap_spec(
        mode=mode if mode in ("freeform", "module") else "freeform",  # type: ignore[arg-type]
        theme=theme,
        character_id=character_id,
        include_faerun=include_faerun,
    )
    return spec.adventure_outline
