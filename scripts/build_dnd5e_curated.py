#!/usr/bin/env python3
"""Build D&D 5e (2024 PHB) curated YAML from docs/dnd5e/player.pdf."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.settings import CURATED_DIR

PDF = ROOT / "docs" / "dnd5e" / "player.pdf"

# Source: PHB 2024 chapter 4 (pp. 180-187) and chapter 3 class trait tables.
BACKGROUNDS = [
    {"id": "acolyte", "label": "Acolyte", "ability_scores": ["int", "wis", "cha"], "feat": "Magic Initiate (Cleric)", "skills": ["insight", "religion"], "tool": "Calligrapher's Supplies"},
    {"id": "artisan", "label": "Artisan", "ability_scores": ["str", "dex", "int"], "feat": "Crafter", "skills": ["investigation", "persuasion"], "tool": "Artisan's Tools"},
    {"id": "charlatan", "label": "Charlatan", "ability_scores": ["dex", "con", "cha"], "feat": "Skilled", "skills": ["deception", "sleight_of_hand"], "tool": "Forgery Kit"},
    {"id": "criminal", "label": "Criminal", "ability_scores": ["dex", "con", "int"], "feat": "Alert", "skills": ["sleight_of_hand", "stealth"], "tool": "Thieves' Tools"},
    {"id": "entertainer", "label": "Entertainer", "ability_scores": ["str", "dex", "cha"], "feat": "Musician", "skills": ["acrobatics", "performance"], "tool": "Musical Instrument"},
    {"id": "farmer", "label": "Farmer", "ability_scores": ["str", "con", "wis"], "feat": "Tough", "skills": ["animal_handling", "nature"], "tool": "Carpenter's Tools"},
    {"id": "guard", "label": "Guard", "ability_scores": ["str", "int", "wis"], "feat": "Alert", "skills": ["athletics", "perception"], "tool": "Gaming Set"},
    {"id": "guide", "label": "Guide", "ability_scores": ["dex", "con", "wis"], "feat": "Magic Initiate (Druid)", "skills": ["stealth", "survival"], "tool": "Cartographer's Tools"},
    {"id": "hermit", "label": "Hermit", "ability_scores": ["con", "wis", "cha"], "feat": "Healer", "skills": ["medicine", "religion"], "tool": "Herbalism Kit"},
    {"id": "merchant", "label": "Merchant", "ability_scores": ["con", "int", "cha"], "feat": "Lucky", "skills": ["animal_handling", "persuasion"], "tool": "Navigator's Tools"},
    {"id": "noble", "label": "Noble", "ability_scores": ["str", "int", "cha"], "feat": "Skilled", "skills": ["history", "persuasion"], "tool": "Gaming Set"},
    {"id": "sage", "label": "Sage", "ability_scores": ["con", "int", "wis"], "feat": "Magic Initiate (Wizard)", "skills": ["arcana", "history"], "tool": "Calligrapher's Supplies"},
    {"id": "sailor", "label": "Sailor", "ability_scores": ["str", "dex", "wis"], "feat": "Tavern Brawler", "skills": ["acrobatics", "perception"], "tool": "Navigator's Tools"},
    {"id": "scribe", "label": "Scribe", "ability_scores": ["dex", "int", "wis"], "feat": "Skilled", "skills": ["investigation", "perception"], "tool": "Calligrapher's Supplies"},
    {"id": "soldier", "label": "Soldier", "ability_scores": ["str", "dex", "con"], "feat": "Savage Attacker", "skills": ["athletics", "intimidation"], "tool": "Gaming Set"},
    {"id": "wayfarer", "label": "Wayfarer", "ability_scores": ["dex", "wis", "cha"], "feat": "Lucky", "skills": ["insight", "stealth"], "tool": "Thieves' Tools"},
]

SPECIES = [
    {"id": "aasimar", "label": "Aasimar", "speed": 30, "size_options": ["medium", "small"], "traits": ["Celestial Resistance", "Darkvision 60 ft.", "Healing Hands", "Light Bearer", "Celestial Revelation (level 3)"]},
    {"id": "dragonborn", "label": "Dragonborn", "speed": 30, "size_options": ["medium"], "traits": ["Draconic Ancestry", "Breath Weapon", "Damage Resistance", "Darkvision 60 ft."]},
    {"id": "dwarf", "label": "Dwarf", "speed": 30, "size_options": ["medium"], "traits": ["Darkvision 120 ft.", "Dwarven Resilience", "Dwarven Toughness", "Stonecunning"]},
    {"id": "elf", "label": "Elf", "speed": 30, "size_options": ["medium"], "traits": ["Darkvision 60 ft.", "Fey Ancestry", "Keen Senses", "Trance"]},
    {"id": "gnome", "label": "Gnome", "speed": 30, "size_options": ["small"], "traits": ["Darkvision 60 ft.", "Gnomish Cunning"]},
    {"id": "goliath", "label": "Goliath", "speed": 35, "size_options": ["medium"], "traits": ["Giant Ancestry", "Large Form (level 5)", "Powerful Build"]},
    {"id": "halfling", "label": "Halfling", "speed": 30, "size_options": ["small"], "traits": ["Brave", "Halfling Nimbleness", "Luck"]},
    {"id": "human", "label": "Human", "speed": 30, "size_options": ["medium", "small"], "traits": ["Resourceful (Heroic Inspiration on Long Rest)", "Skillful (+1 skill)", "Versatile (Origin feat)"]},
    {"id": "orc", "label": "Orc", "speed": 30, "size_options": ["medium"], "traits": ["Adrenaline Rush", "Darkvision 120 ft.", "Relentless Endurance"]},
    {"id": "tiefling", "label": "Tiefling", "speed": 30, "size_options": ["medium", "small"], "traits": ["Darkvision 60 ft.", "Fiendish Legacy", "Otherworldly Presence"]},
]

CLASSES = [
    {
        "id": "barbarian", "label": "Barbarian", "hit_die": 12, "primary_ability": "str",
        "saving_throws": ["str", "con"], "skill_choices": 2,
        "skill_options": ["animal_handling", "athletics", "intimidation", "nature", "perception", "survival"],
        "armor_training": ["light", "medium", "shields"], "spellcasting": None, "subclass_level": 3,
        "subclasses": ["Path of the Berserker", "Path of the Wild Heart", "Path of the World Tree", "Path of the Zealot"],
    },
    {
        "id": "bard", "label": "Bard", "hit_die": 8, "primary_ability": "cha",
        "saving_throws": ["dex", "cha"], "skill_choices": 3, "skill_options": "any",
        "armor_training": ["light"], "spellcasting": "prepared", "spell_list": "bard", "subclass_level": 3,
        "subclasses": ["College of Dance", "College of Glamour", "College of Lore", "College of Valor"],
        "cantrips_by_level": [2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "prepared_by_level": [4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
    },
    {
        "id": "cleric", "label": "Cleric", "hit_die": 8, "primary_ability": "wis",
        "saving_throws": ["wis", "cha"], "skill_choices": 2,
        "skill_options": ["history", "insight", "medicine", "persuasion", "religion"],
        "armor_training": ["light", "medium", "shields"], "spellcasting": "prepared", "spell_list": "cleric", "subclass_level": 3,
        "subclasses": ["Life Domain", "Light Domain", "Trickery Domain", "War Domain"],
        "cantrips_by_level": [3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
        "prepared_by_level": [4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
    },
    {
        "id": "druid", "label": "Druid", "hit_die": 8, "primary_ability": "wis",
        "saving_throws": ["int", "wis"], "skill_choices": 2,
        "skill_options": ["animal_handling", "arcana", "insight", "medicine", "nature", "perception", "religion", "survival"],
        "armor_training": ["light", "shields"], "spellcasting": "prepared", "spell_list": "druid", "subclass_level": 3,
        "subclasses": ["Circle of the Land", "Circle of the Moon", "Circle of the Sea", "Circle of the Stars"],
        "cantrips_by_level": [2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "prepared_by_level": [4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
    },
    {
        "id": "fighter", "label": "Fighter", "hit_die": 10, "primary_ability": "str",
        "saving_throws": ["str", "con"], "skill_choices": 2,
        "skill_options": ["acrobatics", "animal_handling", "athletics", "history", "insight", "intimidation", "perception", "persuasion", "survival"],
        "armor_training": ["light", "medium", "heavy", "shields"], "spellcasting": None, "subclass_level": 3,
        "subclasses": ["Battle Master", "Champion", "Eldritch Knight", "Psi Warrior"],
    },
    {
        "id": "monk", "label": "Monk", "hit_die": 8, "primary_ability": "dex",
        "saving_throws": ["str", "dex"], "skill_choices": 2,
        "skill_options": ["acrobatics", "athletics", "history", "insight", "religion", "stealth"],
        "armor_training": [], "spellcasting": None, "subclass_level": 3,
        "subclasses": ["Warrior of Mercy", "Warrior of Shadow", "Warrior of the Elements", "Warrior of the Open Hand"],
    },
    {
        "id": "paladin", "label": "Paladin", "hit_die": 10, "primary_ability": "str",
        "saving_throws": ["wis", "cha"], "skill_choices": 2,
        "skill_options": ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"],
        "armor_training": ["light", "medium", "heavy", "shields"], "spellcasting": "prepared", "spell_list": "paladin", "subclass_level": 3,
        "subclasses": ["Oath of Devotion", "Oath of Glory", "Oath of the Ancients", "Oath of Vengeance"],
        "cantrips_by_level": [0] * 20,
        "prepared_by_level": [2, 3, 4, 5, 6, 6, 7, 7, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 15, 15],
    },
    {
        "id": "ranger", "label": "Ranger", "hit_die": 10, "primary_ability": "dex",
        "saving_throws": ["str", "dex"], "skill_choices": 3,
        "skill_options": ["animal_handling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"],
        "armor_training": ["light", "medium", "shields"], "spellcasting": "prepared", "spell_list": "ranger", "subclass_level": 3,
        "subclasses": ["Beast Master", "Fey Wanderer", "Gloom Stalker", "Hunter"],
        "cantrips_by_level": [0] * 20,
        "prepared_by_level": [2, 3, 4, 5, 6, 6, 7, 7, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 15, 15],
    },
    {
        "id": "rogue", "label": "Rogue", "hit_die": 8, "primary_ability": "dex",
        "saving_throws": ["dex", "int"], "skill_choices": 4,
        "skill_options": ["acrobatics", "athletics", "deception", "insight", "intimidation", "investigation", "perception", "persuasion", "sleight_of_hand", "stealth"],
        "armor_training": ["light"], "spellcasting": None, "subclass_level": 3,
        "subclasses": ["Arcane Trickster", "Assassin", "Soulknife", "Thief"],
    },
    {
        "id": "sorcerer", "label": "Sorcerer", "hit_die": 6, "primary_ability": "cha",
        "saving_throws": ["con", "cha"], "skill_choices": 2,
        "skill_options": ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"],
        # PHB 2024: the Sorcerer is a *prepared* caster (Spells Prepared column),
        # not Spells Known as in 2014. Counts read from the PHB Sorcerer table.
        "armor_training": [], "spellcasting": "prepared", "spell_list": "sorcerer", "subclass_level": 3,
        "subclasses": ["Aberrant Sorcery", "Clockwork Sorcery", "Draconic Sorcery", "Wild Magic Sorcery"],
        "cantrips_by_level": [4, 4, 4, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
        "prepared_by_level": [2, 4, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
    },
    {
        "id": "warlock", "label": "Warlock", "hit_die": 8, "primary_ability": "cha",
        "saving_throws": ["wis", "cha"], "skill_choices": 2,
        "skill_options": ["arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"],
        "armor_training": ["light"], "spellcasting": "pact", "spell_list": "warlock", "subclass_level": 3,
        "subclasses": ["Archfey Patron", "Celestial Patron", "Fiend Patron", "Great Old One Patron"],
        "cantrips_by_level": [2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
        "pact_slots_by_level": [
            {"slots": 1, "level": 1}, {"slots": 2, "level": 1}, {"slots": 2, "level": 2},
            {"slots": 2, "level": 2}, {"slots": 2, "level": 3}, {"slots": 2, "level": 3},
            {"slots": 2, "level": 4}, {"slots": 2, "level": 4}, {"slots": 2, "level": 5},
            {"slots": 2, "level": 5}, {"slots": 3, "level": 5}, {"slots": 3, "level": 5},
            {"slots": 3, "level": 5}, {"slots": 3, "level": 5}, {"slots": 3, "level": 5},
            {"slots": 3, "level": 5}, {"slots": 4, "level": 5}, {"slots": 4, "level": 5},
            {"slots": 4, "level": 5}, {"slots": 4, "level": 5},
        ],
        "spells_known_by_level": [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15],
    },
    {
        "id": "wizard", "label": "Wizard", "hit_die": 6, "primary_ability": "int",
        "saving_throws": ["int", "wis"], "skill_choices": 2,
        "skill_options": ["arcana", "history", "insight", "investigation", "medicine", "nature", "religion"],
        "armor_training": [], "spellcasting": "prepared", "spell_list": "wizard", "subclass_level": 3,
        "subclasses": ["Abjurer", "Diviner", "Evoker", "Illusionist"],
        "cantrips_by_level": [3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
        "prepared_by_level": [4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
    },
]

# PHB 2024 full caster slot progression (Bard, Cleric, Druid, Sorcerer, Wizard)
FULL_CASTER_SLOTS = {
    1: [2, 0, 0, 0, 0, 0, 0, 0, 0],
    2: [3, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [4, 2, 0, 0, 0, 0, 0, 0, 0],
    4: [4, 3, 0, 0, 0, 0, 0, 0, 0],
    5: [4, 3, 2, 0, 0, 0, 0, 0, 0],
    6: [4, 3, 3, 0, 0, 0, 0, 0, 0],
    7: [4, 3, 3, 1, 0, 0, 0, 0, 0],
    8: [4, 3, 3, 2, 0, 0, 0, 0, 0],
    9: [4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
    11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}

HALF_CASTER_SLOTS_2014 = {
    1: [0, 0, 0, 0, 0],
    2: [2, 0, 0, 0, 0],
    3: [3, 0, 0, 0, 0],
    4: [3, 0, 0, 0, 0],
    5: [4, 2, 0, 0, 0],
    6: [4, 2, 0, 0, 0],
    7: [4, 3, 0, 0, 0],
    8: [4, 3, 0, 0, 0],
    9: [4, 3, 2, 0, 0],
    10: [4, 3, 2, 0, 0],
    11: [4, 3, 3, 0, 0],
    12: [4, 3, 3, 0, 0],
    13: [4, 3, 3, 1, 0],
    14: [4, 3, 3, 1, 0],
    15: [4, 3, 3, 2, 0],
    16: [4, 3, 3, 2, 0],
    17: [4, 3, 3, 3, 1],
    18: [4, 3, 3, 3, 1],
    19: [4, 3, 3, 3, 2],
    20: [4, 3, 3, 3, 2],
}

# 2024 PHB: Paladin and Ranger gain Spellcasting at level 1 (shift slot table down one level).
HALF_CASTER_SLOTS = {1: HALF_CASTER_SLOTS_2014[2]}
HALF_CASTER_SLOTS.update({lvl: HALF_CASTER_SLOTS_2014[lvl] for lvl in range(2, 21)})

SKILLS = [
    {"id": "acrobatics", "label": "Acrobatics", "ability": "dex"},
    {"id": "animal_handling", "label": "Animal Handling", "ability": "wis"},
    {"id": "arcana", "label": "Arcana", "ability": "int"},
    {"id": "athletics", "label": "Athletics", "ability": "str"},
    {"id": "deception", "label": "Deception", "ability": "cha"},
    {"id": "history", "label": "History", "ability": "int"},
    {"id": "insight", "label": "Insight", "ability": "wis"},
    {"id": "intimidation", "label": "Intimidation", "ability": "cha"},
    {"id": "investigation", "label": "Investigation", "ability": "int"},
    {"id": "medicine", "label": "Medicine", "ability": "wis"},
    {"id": "nature", "label": "Nature", "ability": "int"},
    {"id": "perception", "label": "Perception", "ability": "wis"},
    {"id": "performance", "label": "Performance", "ability": "cha"},
    {"id": "persuasion", "label": "Persuasion", "ability": "cha"},
    {"id": "religion", "label": "Religion", "ability": "int"},
    {"id": "sleight_of_hand", "label": "Sleight of Hand", "ability": "dex"},
    {"id": "stealth", "label": "Stealth", "ability": "dex"},
    {"id": "survival", "label": "Survival", "ability": "wis"},
]

ALIGNMENTS = [
    "lawful_good", "neutral_good", "chaotic_good",
    "lawful_neutral", "true_neutral", "chaotic_neutral",
    "lawful_evil", "neutral_evil", "chaotic_evil",
]

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
STANDARD_ARRAY_BY_CLASS = {
    "barbarian": {"str": 15, "dex": 13, "con": 14, "int": 10, "wis": 12, "cha": 8},
    "bard": {"str": 8, "dex": 14, "con": 12, "int": 13, "wis": 10, "cha": 15},
    "cleric": {"str": 14, "dex": 8, "con": 13, "int": 10, "wis": 15, "cha": 12},
    "druid": {"str": 8, "dex": 12, "con": 14, "int": 13, "wis": 15, "cha": 10},
    "fighter": {"str": 15, "dex": 14, "con": 13, "int": 8, "wis": 10, "cha": 12},
    "monk": {"str": 12, "dex": 15, "con": 13, "int": 10, "wis": 14, "cha": 8},
    "paladin": {"str": 15, "dex": 10, "con": 13, "int": 8, "wis": 12, "cha": 14},
    "ranger": {"str": 12, "dex": 15, "con": 13, "int": 8, "wis": 14, "cha": 10},
    "rogue": {"str": 12, "dex": 15, "con": 13, "int": 14, "wis": 10, "cha": 8},
    "sorcerer": {"str": 10, "dex": 13, "con": 14, "int": 12, "wis": 8, "cha": 15},
    "warlock": {"str": 8, "dex": 14, "con": 13, "int": 12, "wis": 10, "cha": 15},
    "wizard": {"str": 8, "dex": 14, "con": 13, "int": 15, "wis": 12, "cha": 10},
}


def _clean_spell_name(raw: str) -> str | None:
    s = re.sub(r"\s+", " ", raw.strip())
    s = re.sub(r"[^A-Za-z0-9' /-]", "", s)
    s = s.strip(" -/")
    if not s or len(s) < 2:
        return None
    if s.lower() in {"spell", "school", "special", "c", "r", "m"}:
        return None
    return s.title()


def extract_spell_lists() -> dict[str, dict[str, list[str]]]:
    from pypdf import PdfReader

    reader = PdfReader(str(PDF))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    lists: dict[str, dict[str, list[str]]] = {}
    pattern = re.compile(
        r"([A-Z][A-Z\s]+?)\s+SPELL\s+LI(?:ST|\.ST)\b(.*?)(?=(?:[A-Z][A-Z\s]+?\s+SPELL\s+LI(?:ST|\.ST)\b)|\Z)",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        class_name = match.group(1).strip().title().replace("  ", " ")
        body = match.group(2)
        class_key = class_name.lower().replace(" ", "_")
        by_level: dict[str, list[str]] = {"cantrips": []}
        current = "cantrips"
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            upper = line.upper()
            if "CANTRIP" in upper or "LEVEL 0" in upper:
                current = "cantrips"
                continue
            m = re.match(r"LEVEL\s+(\d+)", upper)
            if m:
                current = m.group(1)
                by_level.setdefault(current, [])
                continue
            if line.startswith("Spell") and "School" in line:
                continue
            name = _clean_spell_name(line)
            if name:
                by_level.setdefault(current, []).append(name)
        # dedupe preserving order
        for lvl, names in list(by_level.items()):
            seen: set[str] = set()
            deduped = []
            for n in names:
                key = n.lower()
                if key not in seen:
                    seen.add(key)
                    deduped.append(n)
            by_level[lvl] = deduped
        if by_level.get("cantrips") or any(k != "cantrips" for k in by_level):
            lists[class_key] = by_level
    return lists


def write_yaml(name: str, data: dict) -> None:
    path = CURATED_DIR / name
    header = "# D&D 5e (2024 PHB) — auto-built from docs/dnd5e/player.pdf\n"
    path.write_text(header + yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Wrote {path}")


def main() -> int:
    spells = {}  # maintained in data/curated/dnd5e_spells.yaml (hand-verified)
    write_yaml("dnd5e_backgrounds.yaml", {"backgrounds": BACKGROUNDS})
    write_yaml("dnd5e_species.yaml", {"species": SPECIES})
    write_yaml("dnd5e_classes.yaml", {
        "classes": CLASSES,
        "full_caster_slots": {str(k): v for k, v in FULL_CASTER_SLOTS.items()},
        "half_caster_slots": {str(k): v for k, v in HALF_CASTER_SLOTS.items()},
    })
    write_yaml("dnd5e_skills.yaml", {"skills": SKILLS, "alignments": ALIGNMENTS, "standard_array": STANDARD_ARRAY, "standard_array_by_class": STANDARD_ARRAY_BY_CLASS})
    if spells:
        write_yaml("dnd5e_spells.yaml", {"spell_lists": spells})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
