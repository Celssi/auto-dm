"""Format campaign NPC/location journal for the DM prompt."""

from __future__ import annotations

from backend.journal_storage import (
    get_campaign,
    get_campaign_location,
    get_campaign_npc,
    list_campaign_locations,
    list_campaign_npcs,
)
from backend.storage import get_adventure_summary, list_adventures_for_campaign

MAX_BODY = 600
MAX_NPCS = 10
MAX_LOCATIONS = 8
MAX_PRIOR_SUMMARY = 1500
MAX_PRIOR_ADVENTURES = 5


def _clip(text: str, limit: int = MAX_BODY) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def prior_adventures_context(
    campaign_id: str | None,
    *,
    exclude_adventure_id: str | None = None,
    completed_only: bool = False,
) -> str:
    if not campaign_id:
        return ""
    adventures = list_adventures_for_campaign(campaign_id)
    if completed_only:
        adventures = [a for a in adventures if a.get("status") == "completed"]
    parts: list[str] = []
    for adv in adventures:
        adv_id = adv.get("id", "")
        if not adv_id or adv_id == exclude_adventure_id:
            continue
        summary = get_adventure_summary(adv_id).strip()
        if not summary:
            continue
        name = adv.get("name") or adv_id
        parts.append(f"### {name}\n{_clip(summary, MAX_PRIOR_SUMMARY)}")
        if len(parts) >= MAX_PRIOR_ADVENTURES:
            break
    if not parts:
        return ""
    return "## Previous adventures in this campaign\n\n" + "\n\n".join(parts)


def world_context_for_campaign(
    campaign_id: str | None,
    *,
    has_adventure_summary: bool = False,
    exclude_adventure_id: str | None = None,
    for_narrator: bool = False,
) -> str:
    if not campaign_id:
        return ""

    campaign = get_campaign(campaign_id)
    if not campaign:
        return ""

    parts: list[str] = [f"## Campaign: {campaign.get('name', campaign_id)}"]
    if not for_narrator:
        arc = (campaign.get("story_arc") or "").strip()
        if arc:
            arc_limit = 800 if has_adventure_summary else 2000
            parts.append(_clip(arc, arc_limit))

    prior = prior_adventures_context(
        campaign_id,
        exclude_adventure_id=exclude_adventure_id,
        completed_only=for_narrator,
    )
    if prior:
        parts.append(prior)

    npc_rows = list_campaign_npcs(campaign_id)[:MAX_NPCS]
    if npc_rows:
        parts.append("\n### Key NPCs")
        for row in npc_rows:
            npc = get_campaign_npc(campaign_id, row["id"])
            if not npc:
                continue
            parts.append(f"\n**{npc.get('name', row['id'])}**\n{_clip(npc.get('body', ''))}")

    loc_rows = list_campaign_locations(campaign_id)[:MAX_LOCATIONS]
    if loc_rows:
        parts.append("\n### Key locations")
        for row in loc_rows:
            loc = get_campaign_location(campaign_id, row["id"])
            if not loc:
                continue
            parts.append(f"\n**{loc.get('name', row['id'])}**\n{_clip(loc.get('body', ''))}")

    return "\n".join(parts).strip()
