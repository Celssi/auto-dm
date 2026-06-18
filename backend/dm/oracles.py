"""Solo play oracles (ported from ChatDM oracle patterns)."""

from __future__ import annotations

import random
from typing import Any

from backend.dm.curated import roll_oracle

YES_NO_ANSWERS = [
    "Yes",
    "Yes, and…",
    "Yes, but…",
    "No",
    "No, and…",
    "No, but…",
]

LIKELIHOOD_TABLES: dict[str, list[str]] = {
    "almost_certain": ["Yes", "Yes", "Yes, and…", "Yes, but…"],
    "likely": ["Yes", "Yes", "Yes, but…", "No, but…"],
    "fifty_fifty": ["Yes", "Yes, but…", "No", "No, but…"],
    "unlikely": ["No", "No", "No, but…", "Yes, but…"],
    "almost_impossible": ["No", "No", "No, and…", "No, but…"],
}

LOCATION_TYPES = [
    "Ancient ruins",
    "Dense forest",
    "Busy marketplace",
    "Mountain pass",
    "Tavern common room",
    "Cave system",
    "Noble estate",
    "Abandoned temple",
    "Coastal cliff",
    "Swamp hamlet",
    "Underground tunnel",
    "Castle courtyard",
]

ATMOSPHERES = [
    "Tense and foreboding",
    "Peaceful and serene",
    "Chaotic and busy",
    "Mysterious and quiet",
    "Oppressive and dark",
    "Warm and welcoming",
    "Eerie and unsettling",
    "Triumphant and hopeful",
]

WEATHER = [
    "Clear skies",
    "Light rain",
    "Heavy storm",
    "Thick fog",
    "Snow flurries",
    "Blazing heat",
    "Cold wind",
    "Overcast gloom",
]

TIMES_OF_DAY = [
    "Pre-dawn",
    "Morning",
    "Midday",
    "Afternoon",
    "Dusk",
    "Night",
    "Deep night",
]

NPC_TRAITS = [
    "Suspicious merchant",
    "Weary guard",
    "Cheerful innkeeper",
    "Secretive scholar",
    "Gruff blacksmith",
    "Nervous acolyte",
    "Bold adventurer",
    "Mysterious stranger",
]

NPC_MOODS = [
    "Hostile",
    "Wary",
    "Neutral",
    "Friendly",
    "Helpful",
    "Desperate",
    "Amused",
]

DUNGEON_ROOMS = [
    "Empty chamber with cracked pillars",
    "Rubble-filled hall",
    "Flooded cellar",
    "Trapped corridor",
    "Shrine to a forgotten god",
    "Guard post with braziers",
    "Natural cavern with stalactites",
    "Arcane laboratory",
    "Prison cells",
    "Treasure vault (locked)",
    "Collapsing bridge over a chasm",
]

DUNGEON_FEATURES = [
    "Hidden door",
    "Pressure plate trap",
    "Faded murals",
    "Recent footprints",
    "Distant dripping water",
    "Old bloodstains",
    "Flickering magical light",
    "Collapsed ceiling",
    "Iron portcullis",
    "Whispering voices",
]


def yes_or_no() -> dict[str, Any]:
    answer = random.choice(YES_NO_ANSWERS)
    return {"answer": answer, "summary": f"**Yes/No oracle:** {answer}"}


def likelihood(level: str = "fifty_fifty") -> dict[str, Any]:
    key = level.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "almostcertain": "almost_certain",
        "almost_impossible": "almost_impossible",
        "almostimpossible": "almost_impossible",
        "fiftyfifty": "fifty_fifty",
        "50_50": "fifty_fifty",
    }
    key = aliases.get(key, key)
    table = LIKELIHOOD_TABLES.get(key, LIKELIHOOD_TABLES["fifty_fifty"])
    answer = random.choice(table)
    return {
        "likelihood": key,
        "answer": answer,
        "summary": f"**Likelihood ({key.replace('_', ' ')}):** {answer}",
    }


def scene_setup() -> dict[str, Any]:
    loc = random.choice(LOCATION_TYPES)
    atm = random.choice(ATMOSPHERES)
    w = random.choice(WEATHER)
    t = random.choice(TIMES_OF_DAY)
    summary = f"**Scene:** {loc}. {atm}. {w}. {t}."
    return {
        "location": loc,
        "atmosphere": atm,
        "weather": w,
        "time": t,
        "summary": summary,
    }


def generate_npc() -> dict[str, Any]:
    trait = random.choice(NPC_TRAITS)
    mood = random.choice(NPC_MOODS)
    summary = f"**NPC:** {trait} — mood: **{mood}**."
    return {"trait": trait, "mood": mood, "summary": summary}


def dungeon_room() -> dict[str, Any]:
    room = random.choice(DUNGEON_ROOMS)
    feature = random.choice(DUNGEON_FEATURES)
    summary = f"**Dungeon room:** {room}. Notable: {feature}."
    return {"room": room, "feature": feature, "summary": summary}


ORACLE_TOOLS: dict[str, dict[str, str]] = {
    "yes_or_no": {"label": "Yes / No", "kind": "oracle"},
    "likelihood": {"label": "Likelihood", "kind": "oracle"},
    "scene_setup": {"label": "Scene setup", "kind": "oracle"},
    "generate_npc": {"label": "Generate NPC", "kind": "oracle"},
    "dungeon_room": {"label": "Dungeon room", "kind": "oracle"},
    "oracle_d6": {"label": "Solo oracle (d6)", "kind": "oracle"},
}


def run_oracle(oracle_id: str, *, likelihood_level: str = "fifty_fifty") -> dict[str, Any]:
    if oracle_id == "yes_or_no":
        return yes_or_no()
    if oracle_id == "likelihood":
        return likelihood(likelihood_level)
    if oracle_id == "scene_setup":
        return scene_setup()
    if oracle_id == "generate_npc":
        return generate_npc()
    if oracle_id == "dungeon_room":
        return dungeon_room()
    if oracle_id == "oracle_d6":
        return roll_oracle()
    raise ValueError(f"Unknown oracle: {oracle_id}")
