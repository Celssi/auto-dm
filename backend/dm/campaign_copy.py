"""Copy a campaign for replay with a different character (reset play state)."""

from __future__ import annotations

from typing import Any

from backend.dm.encounters import load_adventure_encounters, save_adventure_encounters
from backend.dm.story_director import StoryProgress, load_story_progress, save_story_progress
from backend.journal_storage import (
    _unique_id,
    get_campaign,
    get_campaign_location,
    get_campaign_npc,
    list_campaign_locations,
    list_campaign_npcs,
    list_campaigns,
    save_campaign,
    save_campaign_location,
    save_campaign_npc,
    slugify,
)
from backend.storage import (
    get_adventure,
    get_character,
    list_adventures,
    list_adventures_for_campaign,
    save_adventure,
    write_adventure_summary,
)

_PLOT_UPDATE_MARKER = "\n\n[Plot update]\n"


def _base_story_arc(story_arc: str) -> str:
    text = (story_arc or "").strip()
    if not text:
        return ""
    idx = text.find(_PLOT_UPDATE_MARKER)
    return text[:idx].strip() if idx >= 0 else text


def _reset_progress(progress: StoryProgress) -> StoryProgress:
    checkpoints = [
        cp.model_copy(update={"status": "active" if i == 0 else "pending"})
        for i, cp in enumerate(progress.checkpoints)
    ]
    stage_label = checkpoints[0].title if checkpoints else progress.stage_label
    return StoryProgress(stage_label=stage_label, checkpoints=checkpoints, guidance="")


def _fresh_adventure_log(adventure_name: str, campaign_name: str, sequence: int | None) -> str:
    seq = int(sequence or 1)
    if seq > 1:
        return f"# Adventure log\n\n_Planned adventure {seq} in {campaign_name}._\n"
    return f"# Adventure log\n\n_Fresh start — {adventure_name} in {campaign_name}._\n"


def copy_campaign(
    source_campaign_id: str,
    *,
    character_id: str,
    name: str = "",
) -> dict[str, Any]:
    """Duplicate campaign structure; reset logs, progress, and plot updates for a new run."""
    char_id = character_id.strip()
    if not char_id:
        raise ValueError("character_id is required")
    if not get_character(char_id):
        raise ValueError("Character not found")

    source = get_campaign(source_campaign_id)
    if not source:
        raise ValueError("Campaign not found")

    char_name = str(get_character(char_id).get("name") or char_id)
    default_name = f"{source.get('name', 'Campaign')} ({char_name})"
    new_name = name.strip() or default_name

    existing_campaign_ids = {row["id"] for row in list_campaigns()}
    new_campaign_id = _unique_id(slugify(new_name), existing_campaign_ids)

    campaign_payload: dict[str, Any] = {
        "name": new_name,
        "story_arc": _base_story_arc(str(source.get("story_arc") or "")),
        "status": "active",
        "character_ids": [char_id],
        "copied_from": source_campaign_id,
    }
    for key in ("generation_mode", "source_module", "theme", "adventure_count"):
        if source.get(key) not in (None, "", {}):
            campaign_payload[key] = source[key]

    save_campaign(new_campaign_id, campaign_payload)

    for row in list_campaign_npcs(source_campaign_id):
        npc = get_campaign_npc(source_campaign_id, row["id"])
        if npc:
            save_campaign_npc(
                new_campaign_id, row["id"], {"name": npc["name"], "body": npc.get("body", "")}
            )

    for row in list_campaign_locations(source_campaign_id):
        loc = get_campaign_location(source_campaign_id, row["id"])
        if loc:
            save_campaign_location(
                new_campaign_id, row["id"], {"name": loc["name"], "body": loc.get("body", "")}
            )

    source_adventures = sorted(
        list_adventures_for_campaign(source_campaign_id),
        key=lambda a: int(a.get("sequence") or 0),
    )
    existing_adv_ids = {a["id"] for a in list_adventures()}
    new_adventure_ids: list[str] = []

    for i, adv_meta in enumerate(source_adventures):
        src_id = adv_meta.get("id")
        if not src_id:
            continue
        src = get_adventure(src_id)
        if not src:
            continue

        adv_name = str(src.get("name") or src_id)
        new_adv_id = _unique_id(slugify(f"{new_campaign_id}-{adv_name}"), existing_adv_ids)
        existing_adv_ids.add(new_adv_id)

        sequence = src.get("sequence")
        status = "active" if i == 0 else "planned"
        outline = str(src.get("outline") or "")
        log = _fresh_adventure_log(adv_name, new_name, sequence if sequence is not None else i + 1)

        meta = {
            k: v
            for k, v in src.items()
            if k
            in (
                "mode",
                "theme",
                "include_faerun",
                "sequence",
                "source_module",
            )
        }
        meta.update(
            {
                "name": adv_name,
                "character_id": char_id,
                "campaign_id": new_campaign_id,
                "status": status,
            }
        )

        save_adventure(new_adv_id, meta, outline=outline, log=log)
        write_adventure_summary(new_adv_id, "")

        encounters = load_adventure_encounters(src_id)
        if encounters:
            save_adventure_encounters(new_adv_id, encounters)

        progress = load_story_progress(src_id)
        if progress and progress.checkpoints:
            save_story_progress(new_adv_id, _reset_progress(progress))

        new_adventure_ids.append(new_adv_id)

    return {
        "campaign_id": new_campaign_id,
        "campaign": get_campaign(new_campaign_id),
        "adventure_ids": new_adventure_ids,
        "copied_from": source_campaign_id,
    }
