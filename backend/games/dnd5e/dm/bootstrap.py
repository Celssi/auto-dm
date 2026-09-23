"""D&D 5e campaign bootstrap."""

from __future__ import annotations

from typing import Any, Literal

from backend.dm.campaign_bootstrap import (
    BootstrapMode,
    generate_bootstrap_spec,
)
from backend.dm.campaign_repair import extract_encounters_from_outline
from backend.dm.encounters import save_adventure_encounters
from backend.dm.opening_scene import _generate_opening_from_outline, _generate_standalone_opening
from backend.dm.session_opening import attach_opening_to_session
from backend.dm.story_director import ensure_story_progress
from backend.dm.story_memory import generate_opening_summary
from backend.journal_storage import (
    save_campaign,
    save_campaign_location,
    save_campaign_npc,
    slugify,
)
from backend.storage import (
    create_session,
    save_adventure,
    write_adventure_summary,
)


def _clean_opening(text: str) -> str:
    from backend.dm.prose_style import sanitize_narration_dashes

    return sanitize_narration_dashes((text or "").strip())


def bootstrap_dnd_campaign(
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
    opening = _clean_opening(spec.opening_scene)
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
        log=(f"# Adventure log\n\n_Bootstrap opening scene logged._\n\n{opening}\n"),
    )

    npc_hints = "\n".join(f"- {n.name}: {n.body[:200]}" for n in spec.npcs[:8])
    summary = generate_opening_summary(
        log=opening,
        opening_scene=opening,
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
    attach_opening_to_session(session_id=session_id, opening=opening)

    return {
        "session_id": session_id,
        "campaign_id": campaign_id,
        "adventure_id": adventure_id,
        "opening_scene": opening,
        "counts": {"npcs": len(spec.npcs), "locations": len(spec.locations)},
    }


def generate_dnd_opening(char: dict, adv: dict | None = None) -> str:
    adv = adv or {}
    adventure_id = adv.get("id", "")
    campaign_id = (adv.get("campaign_id") or "").strip()
    mode: Literal["freeform", "module"] = (
        adv.get("mode", "freeform") if adv.get("mode") in ("freeform", "module") else "freeform"
    )
    theme = (adv.get("theme") or adv.get("name") or "").strip()
    outline = (adv.get("outline") or "").strip()
    if outline:
        return _generate_opening_from_outline(
            adventure_name=adv.get("name", adventure_id),
            theme=theme,
            char=char,
            outline=outline,
            campaign_id=campaign_id,
        )
    return _generate_standalone_opening(
        mode=mode,
        theme=theme or adv.get("name", "Adventure"),
        character_id=str(char.get("id") or ""),
        include_faerun=bool(adv.get("include_faerun")),
        adventure_name=adv.get("name", ""),
    )
