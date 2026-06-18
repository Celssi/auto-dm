"""Repair campaign journal and encounters from story arc and adventure outlines."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from backend.dm.encounters import (
    EncounterEnemySpec,
    EncounterSpec,
    new_encounter_id,
    save_adventure_encounters,
)
from backend.dm.story_director import ensure_story_progress, load_story_progress
from backend.journal_storage import get_campaign, save_campaign_location, save_campaign_npc, slugify
from backend.llm import get_langchain_chat_llm
from backend.storage import get_adventure, list_adventures_for_campaign


class JournalEntryExtract(BaseModel):
    name: str
    body: str = Field(description="Appearance, role, personality, current status")


class EncounterEnemyExtract(BaseModel):
    monster_name: str = Field(description="Canonical D&D 5e Monster Manual name")
    count: int = Field(default=1, ge=1, le=8)
    label: str = ""


class EncounterExtract(BaseModel):
    name: str
    trigger_beat: str = ""
    description: str = ""
    enemies: list[EncounterEnemyExtract] = Field(default_factory=list)


class AdventureEncountersSpec(BaseModel):
    encounters: list[EncounterExtract] = Field(default_factory=list)


class JournalExtractSpec(BaseModel):
    npcs: list[JournalEntryExtract] = Field(default_factory=list)
    locations: list[JournalEntryExtract] = Field(default_factory=list)
    encounters_by_adventure: dict[str, list[EncounterExtract]] = Field(
        default_factory=dict,
        description="Adventure name -> list of encounters with MM monster names",
    )


WAKING_DEEP_ENCOUNTERS: dict[str, list[EncounterSpec]] = {
    "the-drowned-bargain": [
        EncounterSpec(
            id="merrow-raid",
            name="Merrow Harbor Raid",
            trigger_beat="Merrow raid",
            description="Merrow attack Salthollow docks.",
            enemies=[EncounterEnemySpec(monster_name="Merrow", count=3, label="Harbor raider")],
        ),
        EncounterSpec(
            id="sunken-sanctum",
            name="Sunken Sanctum Guardian",
            trigger_beat="Priestess",
            description="Corrupted sahuagin guard the Crown fragment.",
            enemies=[
                EncounterEnemySpec(monster_name="Sahuagin Priest", count=1, label="Priestess"),
                EncounterEnemySpec(monster_name="Sahuagin", count=2, label="Guard"),
            ],
        ),
    ],
    "the-privateers-gambit": [
        EncounterSpec(
            id="vault-sentinel",
            name="Vault Sentinel",
            trigger_beat="Vault",
            description="Arcane ward guardians aboard the Sovereign's Mandate.",
            enemies=[EncounterEnemySpec(monster_name="Mage", count=1, label="Sylene's sentinel")],
        ),
        EncounterSpec(
            id="admiral-guard",
            name="Admiral's Guard",
            trigger_beat="Greave",
            description="Iron Admiralty marines during the escape.",
            enemies=[EncounterEnemySpec(monster_name="Knight", count=2, label="Marine")],
        ),
    ],
    "the-maw-below": [
        EncounterSpec(
            id="dragon-turtle",
            name="Mad Dragon Turtle",
            trigger_beat="Dragon turtle",
            description="Psychic-influenced dragon turtle attacks the Gilded Eel.",
            enemies=[EncounterEnemySpec(monster_name="Dragon Turtle", count=1)],
        ),
        EncounterSpec(
            id="volcano-assault",
            name="Ashenmaw Ascent",
            trigger_beat="Ashenmaw",
            description="Drowned Disciples and elementals on the volcano.",
            enemies=[
                EncounterEnemySpec(monster_name="Merrow", count=3, label="War party"),
                EncounterEnemySpec(monster_name="Earth Elemental", count=1),
            ],
        ),
        EncounterSpec(
            id="ulvorith-boss",
            name="Speaker Ulvorith",
            trigger_beat="Ulvorith",
            description="Boss fight at the Stones of First Tide.",
            enemies=[
                EncounterEnemySpec(monster_name="Sea Spawn", count=1, label="Speaker Ulvorith"),
                EncounterEnemySpec(monster_name="Sahuagin", count=2),
            ],
        ),
        EncounterSpec(
            id="ritual-wave",
            name="Rising Horrors",
            trigger_beat="Ritual",
            description="Deep-sea horrors during the Binding Ritual.",
            enemies=[
                EncounterEnemySpec(monster_name="Deep Scion", count=1),
                EncounterEnemySpec(monster_name="Merrow", count=2),
            ],
        ),
    ],
}

WAKING_DEEP_NPCS: list[JournalEntryExtract] = [
    JournalEntryExtract(
        name="Captain Marceska Venn",
        body="Half-orc pirate captain of the Gilded Eel. Pragmatic leader of the Tide Moot in Salthollow.",
    ),
    JournalEntryExtract(
        name="Old Thessan",
        body="Weathered tortle druid, last remnant of the Circle of Salt and Storm. Hides in Salthollow slums.",
    ),
    JournalEntryExtract(
        name="Speaker Ulvorith",
        body="Sea elf warlock and cult leader of the Drowned Disciples. Wields a corrupted Crown fragment.",
    ),
    JournalEntryExtract(
        name="Admiral Harlan Greave",
        body="Iron Admiralty commander seeking to weaponize Maw-of-the-Void for Valdremere.",
    ),
    JournalEntryExtract(
        name="Pip Galesong",
        body="Gnome spy and forger. Expert at infiltration and false credentials.",
    ),
    JournalEntryExtract(
        name="Sylene Ashford",
        body="Admiral Greave's mage advisor aboard the Sovereign's Mandate. Detects magic.",
    ),
]

WAKING_DEEP_LOCATIONS: list[JournalEntryExtract] = [
    JournalEntryExtract(
        name="Salthollow",
        body="Lawless port city built into sea cliffs. Home of the Tide Moot.",
    ),
    JournalEntryExtract(
        name="Drowning Trench",
        body="Abyssal trench where Maw-of-the-Void stirs beneath the Amber Sea.",
    ),
    JournalEntryExtract(
        name="Ashenmaw",
        body="Volcanic island wreathed in toxic fumes. Site of the Stones of First Tide.",
    ),
    JournalEntryExtract(
        name="Stones of First Tide",
        body="Ancient druidic henge on Ashenmaw's caldera rim. Place of the Binding Ritual.",
    ),
    JournalEntryExtract(
        name="Fort Tidecrest",
        body="Heavily fortified Iron Admiralty garrison island.",
    ),
    JournalEntryExtract(
        name="Sunken Sanctum of Eryloss",
        body="Submerged temple holding the first Crown fragment.",
    ),
]


def extract_journal_from_text(
    story_arc: str,
    adventure_outlines: list[tuple[str, str]],
) -> JournalExtractSpec:
    """LLM extraction of NPCs, locations, and encounters from campaign text."""
    adventures_block = "\n\n".join(
        f"### {name}\n{outline[:3000]}" for name, outline in adventure_outlines
    )
    prompt = f"""Extract campaign journal data for a D&D 5e solo campaign.

Story arc:
{story_arc[:6000]}

Adventures:
{adventures_block[:12000]}

Rules:
- npcs: 4-10 key named characters (not the solo player hero unless listed as NPC ally)
- locations: 3-8 key places
- encounters_by_adventure: for EACH adventure name, 2-4 combat encounters using canonical Monster Manual creature names
- trigger_beat: short story beat title when encounter starts
- enemies: use real MM names (Merrow, Sahuagin, Dragon Turtle, etc.)
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(JournalExtractSpec)
    return llm.invoke([HumanMessage(content=prompt)])


def extract_encounters_from_outline(outline: str, adventure_name: str = "") -> list[EncounterSpec]:
    outline = (outline or "").strip()
    if not outline:
        return []
    prompt = f"""Extract 2-4 combat encounters from this D&D adventure outline.

Adventure: {adventure_name}
Outline:
{outline[:5000]}

Use canonical Monster Manual creature names only. Include trigger_beat matching a story beat title.
"""
    llm = get_langchain_chat_llm("claude").with_structured_output(AdventureEncountersSpec)
    spec = llm.invoke([HumanMessage(content=prompt)])
    return [
        EncounterSpec(
            id=new_encounter_id(e.name),
            name=e.name,
            trigger_beat=e.trigger_beat,
            description=e.description,
            enemies=[
                EncounterEnemySpec(monster_name=en.monster_name, count=en.count, label=en.label)
                for en in e.enemies
            ],
        )
        for e in spec.encounters
    ]


def save_journal_entries(campaign_id: str, spec: JournalExtractSpec) -> dict[str, int]:
    counts = {"npcs": 0, "locations": 0, "encounters": 0}
    for npc in spec.npcs:
        if npc.name.strip():
            save_campaign_npc(campaign_id, slugify(npc.name), {"name": npc.name, "body": npc.body})
            counts["npcs"] += 1
    for loc in spec.locations:
        if loc.name.strip():
            save_campaign_location(
                campaign_id, slugify(loc.name), {"name": loc.name, "body": loc.body}
            )
            counts["locations"] += 1
    for adv in list_adventures_for_campaign(campaign_id):
        adv_id = adv.get("id", "")
        adv_name = adv.get("name", "")
        if not adv_id:
            continue
        enc_list = (
            spec.encounters_by_adventure.get(adv_name)
            or spec.encounters_by_adventure.get(adv_id)
            or []
        )
        if enc_list:
            encounters = [
                EncounterSpec(
                    id=new_encounter_id(e.name),
                    name=e.name,
                    trigger_beat=e.trigger_beat,
                    description=e.description,
                    enemies=[
                        EncounterEnemySpec(
                            monster_name=en.monster_name,
                            count=en.count,
                            label=en.label,
                        )
                        for en in e.enemies
                    ],
                )
                for e in enc_list
            ]
            save_adventure_encounters(adv_id, encounters)
            counts["encounters"] += len(encounters)
    return counts


def repair_campaign(campaign_id: str, *, use_llm: bool = True) -> dict[str, Any]:
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign not found: {campaign_id}")

    story_arc = (campaign.get("story_arc") or "").strip()
    adventures = list_adventures_for_campaign(campaign_id)
    outlines: list[tuple[str, str]] = []
    for adv in adventures:
        adv_id = adv.get("id", "")
        full = get_adventure(adv_id) if adv_id else None
        if full:
            outlines.append((adv.get("name", adv_id), full.get("outline") or ""))

    if campaign_id == "the-waking-deep-tides-of-the-shattered-crown":
        spec = JournalExtractSpec(
            npcs=WAKING_DEEP_NPCS,
            locations=WAKING_DEEP_LOCATIONS,
        )
        counts = save_journal_entries(campaign_id, spec)
        enc_total = 0
        for adv in adventures:
            adv_id = adv.get("id", "")
            if adv_id in WAKING_DEEP_ENCOUNTERS:
                save_adventure_encounters(adv_id, WAKING_DEEP_ENCOUNTERS[adv_id])
                enc_total += len(WAKING_DEEP_ENCOUNTERS[adv_id])
        counts["encounters"] = enc_total
    elif use_llm and story_arc:
        spec = extract_journal_from_text(story_arc, outlines)
        counts = save_journal_entries(campaign_id, spec)
    else:
        counts = {"npcs": 0, "locations": 0, "encounters": 0}

    progress_fixed = 0
    for adv in adventures:
        adv_id = adv.get("id", "")
        if not adv_id:
            continue
        full = get_adventure(adv_id)
        outline = (full or {}).get("outline") or ""
        if outline and not load_story_progress(adv_id):
            try:
                ensure_story_progress(adv_id, outline)
                progress_fixed += 1
            except Exception:
                pass

    return {
        "campaign_id": campaign_id,
        "counts": counts,
        "progress_initialized": progress_fixed,
    }
