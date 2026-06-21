"""PHB 2024 origin feat normalization and mechanical hooks."""

from __future__ import annotations

from typing import Any

from backend.characters.entity import Dnd5eCharacter
from backend.characters.multiclass import total_class_level
from backend.characters.spell_resources import normalize_spell_name

ORIGIN_FEAT_LABELS = {
    "alert": "Alert",
    "crafter": "Crafter",
    "healer": "Healer",
    "lucky": "Lucky",
    "magic_initiate_cleric": "Magic Initiate (Cleric)",
    "magic_initiate_druid": "Magic Initiate (Druid)",
    "magic_initiate_wizard": "Magic Initiate (Wizard)",
    "musician": "Musician",
    "savage_attacker": "Savage Attacker",
    "skilled": "Skilled",
    "tavern_brawler": "Tavern Brawler",
    "tough": "Tough",
}

_SKILL_IDS = frozenset(
    {
        "acrobatics",
        "animal_handling",
        "arcana",
        "athletics",
        "deception",
        "history",
        "insight",
        "intimidation",
        "investigation",
        "medicine",
        "nature",
        "perception",
        "performance",
        "persuasion",
        "religion",
        "sleight_of_hand",
        "stealth",
        "survival",
    }
)

# Passive effects surfaced on the sheet / summary (rules reminders, not full automation).
ORIGIN_FEAT_PASSIVES: dict[str, list[str]] = {
    "alert": ["Add proficiency bonus to initiative rolls", "Initiative Swap with a willing ally"],
    "crafter": [
        "20% discount on nonmagical purchases",
        "Fast Crafting on long rest (3 artisan's tools)",
    ],
    "healer": ["Battle Medic with healer's kit", "Reroll healing dice that show 1"],
    "lucky": [
        "Luck points equal to proficiency bonus (long rest)",
        "Spend 1 point for advantage or impose disadvantage",
    ],
    "magic_initiate_cleric": ["2 cleric cantrips + 1 cleric 1st-level spell / long rest"],
    "magic_initiate_druid": ["2 druid cantrips + 1 druid 1st-level spell / long rest"],
    "magic_initiate_wizard": ["2 wizard cantrips + 1 wizard 1st-level spell / long rest"],
    "musician": [
        "Heroic Inspiration to allies after rest (3 instruments)",
        "3 musical instrument proficiencies",
    ],
    "savage_attacker": ["Once per turn: reroll weapon damage dice on hit, use either roll"],
    "skilled": ["3 skill or tool proficiencies"],
    "tavern_brawler": [
        "Unarmed Strike: 1d4 + STR bludgeoning",
        "Improvised weapon proficiency",
        "Push 5 ft. on unarmed hit (1/turn)",
    ],
    "tough": ["+2 max HP per character level"],
}


def normalize_origin_feat_id(raw: str) -> str:
    """Map stored feat label or id to canonical origin feat id."""
    text = str(raw or "").strip()
    if not text:
        return ""
    key = text.lower().replace(" ", "_")
    if key in ORIGIN_FEAT_LABELS:
        return key
    norm = normalize_spell_name(text)
    for fid, label in ORIGIN_FEAT_LABELS.items():
        if normalize_spell_name(label) == norm:
            return fid
        if normalize_spell_name(fid.replace("_", " ")) == norm:
            return fid
    return key


def origin_feat_ids(char: Dnd5eCharacter) -> set[str]:
    ids: set[str] = set()
    for raw in (char.origin_feat, char.versatile_origin_feat):
        fid = normalize_origin_feat_id(raw)
        if fid:
            ids.add(fid)
    return ids


def has_origin_feat(char: Dnd5eCharacter, feat_id: str) -> bool:
    return normalize_origin_feat_id(feat_id) in origin_feat_ids(char)


def feat_matches_when_list(when: list[Any], char: Dnd5eCharacter) -> bool:
    active = origin_feat_ids(char)
    for entry in when:
        wid = normalize_origin_feat_id(str(entry))
        if wid and wid in active:
            return True
    return False


def tough_hp_bonus(char: Dnd5eCharacter) -> int:
    if not has_origin_feat(char, "tough"):
        return 0
    return 2 * max(1, total_class_level(char) or int(char.level or 1))


def luck_points_max(char: Dnd5eCharacter) -> int:
    if not has_origin_feat(char, "lucky"):
        return 0
    return char.proficiency_bonus()


def apply_origin_feat_proficiencies(char: Dnd5eCharacter) -> None:
    """Apply automatic proficiencies from origin feats (no player pick required)."""
    tools = list(char.tool_proficiencies or [])
    if has_origin_feat(char, "tavern_brawler"):
        if "improvised_weapons" not in tools:
            tools.append("improvised_weapons")
    char.tool_proficiencies = tools


def apply_proficiency_pick(pick: str, skills: list[str], tools: list[str]) -> None:
    pid = str(pick or "").strip().lower()
    if not pid:
        return
    if pid in _SKILL_IDS:
        if pid not in skills:
            skills.append(pid)
    elif pid not in tools:
        tools.append(pid)


def origin_feat_passive_lines(char: Dnd5eCharacter) -> list[dict[str, str]]:
    """Display lines for passive origin feat effects on the character sheet."""
    lines: list[dict[str, str]] = []
    for fid in sorted(origin_feat_ids(char)):
        label = ORIGIN_FEAT_LABELS.get(fid, fid.replace("_", " ").title())
        for text in ORIGIN_FEAT_PASSIVES.get(fid, []):
            lines.append({"feat_id": fid, "feat": label, "effect": text})
    return lines
