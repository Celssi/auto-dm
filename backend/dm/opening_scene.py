"""Opening scene generation for new or empty play sessions."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.characters.entity import character_from_dict, format_for_prompt
from backend.dm.campaign_bootstrap import (
    BootstrapMode,
    generate_adventure_spec_for_campaign,
    generate_bootstrap_spec,
)
from backend.dm.session_opening import attach_opening_to_session
from backend.dm.story_director import ensure_story_progress
from backend.dm.story_memory import generate_opening_summary
from backend.dm.world_context import world_context_for_campaign
from backend.journal_storage import get_campaign, save_campaign_location, save_campaign_npc, slugify
from backend.llm import get_langchain_chat_llm
from backend.storage import (
    append_adventure_log,
    get_adventure,
    get_character,
    get_session,
    save_adventure,
    write_adventure_summary,
)


class OpeningScenePackage(BaseModel):
    opening_scene: str = Field(
        description="2-4 paragraphs of in-world DM narration; end with a clear choice"
    )


def _session_has_opening(messages: list[dict] | None) -> bool:
    return any(
        m.get("role") == "assistant" and (m.get("content") or "").strip() for m in messages or []
    )


def _generate_opening_from_outline(
    *,
    adventure_name: str,
    theme: str,
    char: dict,
    outline: str,
    campaign_id: str = "",
) -> str:
    char_obj = character_from_dict(char)
    world = world_context_for_campaign(campaign_id) if campaign_id else ""
    llm = get_langchain_chat_llm("claude").with_structured_output(OpeningScenePackage)
    pkg = llm.invoke(
        [
            HumanMessage(
                content=f"""Write the opening scene for this D&D 5e solo adventure.

Adventure: {adventure_name}
Theme: {theme}

Player character:
{format_for_prompt(char_obj)}

Outline:
{outline[:4000]}

World context:
{world[:3000] or "(none)"}
""",
            ),
        ]
    )
    return pkg.opening_scene.strip()


def _generate_standalone_opening(
    *,
    mode: BootstrapMode,
    theme: str,
    character_id: str,
    include_faerun: bool,
    adventure_name: str = "",
) -> str:
    spec = generate_bootstrap_spec(
        mode=mode,
        theme=theme,
        character_id=character_id,
        include_faerun=include_faerun,
    )
    llm = get_langchain_chat_llm("claude").with_structured_output(OpeningScenePackage)
    prompt = f"""Write the opening scene for a D&D 5e solo adventure.

Adventure: {adventure_name or spec.adventure_name}
Theme: {theme}
Outline excerpt:
{spec.adventure_outline[:2500]}

Use this draft opening as inspiration (you may rewrite):
{spec.opening_scene[:2000]}
"""
    pkg = llm.invoke([HumanMessage(content=prompt)])
    return pkg.opening_scene.strip()


def begin_session(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise ValueError("Session not found")
    if _session_has_opening(session.get("messages")):
        raise ValueError("Session already has an opening scene")

    character_id = session.get("character_id") or ""
    adventure_id = session.get("adventure_id") or ""
    if not character_id or not adventure_id:
        raise ValueError("Session is missing character or adventure")

    char = get_character(character_id)
    adv = get_adventure(adventure_id)
    if not char or not adv:
        raise ValueError("Character or adventure not found")

    campaign_id = (adv.get("campaign_id") or "").strip()
    mode: BootstrapMode = (
        adv.get("mode", "freeform") if adv.get("mode") in ("freeform", "module") else "freeform"
    )
    include_faerun = bool(session.get("include_faerun") or adv.get("include_faerun"))
    theme = (adv.get("theme") or adv.get("name") or "").strip()
    outline = (adv.get("outline") or "").strip()

    if outline:
        opening = _generate_opening_from_outline(
            adventure_name=adv.get("name", adventure_id),
            theme=theme,
            char=char,
            outline=outline,
            campaign_id=campaign_id,
        )
        if campaign_id:
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
        else:
            append_adventure_log(adventure_id, opening)
    elif campaign_id:
        try:
            spec = generate_adventure_spec_for_campaign(
                campaign_id=campaign_id,
                mode=mode,
                theme=theme,
                character_id=character_id,
                include_faerun=include_faerun,
                adventure_name=adv.get("name", ""),
            )
        except Exception:
            campaign = get_campaign(campaign_id)
            story_arc = (campaign.get("story_arc") or "").strip() if campaign else ""
            fallback_outline = f"# {adv.get('name', adventure_id)}\n\n## Premise\n{theme}\n\n## Campaign context\n{story_arc[:4000]}"
            opening = _generate_opening_from_outline(
                adventure_name=adv.get("name", adventure_id),
                theme=theme,
                char=char,
                outline=fallback_outline,
                campaign_id=campaign_id,
            )
            save_adventure(
                adventure_id,
                {**adv, "status": "active"},
                outline=fallback_outline,
                log=f"# Adventure log\n\n{opening}\n",
            )
            summary = generate_opening_summary(
                log=opening,
                opening_scene=opening,
            )
            write_adventure_summary(adventure_id, summary)
            saved_outline = fallback_outline
            if saved_outline:
                ensure_story_progress(adventure_id, saved_outline)
            result = attach_opening_to_session(session_id=session_id, opening=opening)
            result["session_id"] = session_id
            result["adventure_id"] = adventure_id
            return result

        opening = spec.opening_scene.strip()
        if not opening:
            opening = _generate_opening_from_outline(
                adventure_name=adv.get("name", adventure_id),
                theme=theme,
                char=char,
                outline=spec.adventure_outline,
                campaign_id=campaign_id,
            )

        campaign = get_campaign(campaign_id)
        if campaign:
            for npc in spec.new_npcs:
                save_campaign_npc(
                    campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body}
                )
            for loc in spec.new_locations:
                save_campaign_location(
                    campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body}
                )

        save_adventure(
            adventure_id,
            {**adv, "status": "active"},
            outline=spec.adventure_outline,
            log=f"# Adventure log\n\n{opening}\n",
        )
        summary = generate_opening_summary(
            log=opening,
            opening_scene=opening,
        )
        write_adventure_summary(adventure_id, summary)
    else:
        opening = _generate_standalone_opening(
            mode=mode,
            theme=theme or adv.get("name", "Adventure"),
            character_id=character_id,
            include_faerun=include_faerun,
            adventure_name=adv.get("name", ""),
        )
        append_adventure_log(adventure_id, opening)

    saved_outline = (get_adventure(adventure_id) or {}).get("outline") or outline
    if saved_outline:
        ensure_story_progress(adventure_id, saved_outline)

    result = attach_opening_to_session(session_id=session_id, opening=opening)
    result["session_id"] = session_id
    result["adventure_id"] = adventure_id
    return result
