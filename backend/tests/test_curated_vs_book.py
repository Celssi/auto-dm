"""Key 2024 PHB values from the RAG audit, checked against curated YAML."""

from __future__ import annotations

import yaml

from backend.config import CURATED_DIR
from backend.games.dnd5e.characters.character_data import get_weapon, list_weapons
from backend.games.dnd5e.characters.entity import Dnd5eCharacter, format_for_prompt
from backend.games.dnd5e.dm.structured_lookup import lookup_curated_rules, rewrite_rules_query


def _yaml(name: str):
    return yaml.safe_load((CURATED_DIR / name).read_text(encoding="utf-8"))


def test_weapon_catalog_has_38_phb_weapons_with_mastery():
    allowed = {"cleave", "graze", "nick", "push", "sap", "slow", "topple", "vex"}
    weapons = list_weapons()
    assert len(weapons) == 38
    missing = [w["id"] for w in weapons if str(w.get("mastery") or "").lower() not in allowed]
    assert missing == []
    shortbow = get_weapon("shortbow")
    assert shortbow and shortbow.get("mastery") == "vex"
    assert get_weapon("halberd")
    assert get_weapon("glaive")
    assert get_weapon("pistol")


def test_weapon_mastery_summaries_match_2024():
    props = _yaml("dnd5e_weapon_mastery.yaml")["properties"]
    assert "Strength save" not in props["push"]["summary"]
    assert "Large" in props["push"]["summary"]
    assert "Constitution" in props["topple"]["summary"]
    assert "Dexterity" not in props["topple"]["summary"]
    assert "once per turn" in props["cleave"]["summary"].lower()
    assert "once per turn" in props["nick"]["summary"].lower()
    assert "does not stack" in props["slow"]["summary"].lower()
    assert "deals damage" in props["vex"]["summary"].lower() or "deal damage" in props["vex"]["summary"].lower()


def test_fighter_heavy_package_lists_chain_mail_and_greatsword():
    data = _yaml("dnd5e_equipment.yaml")
    heavy = next(p for p in data["class_starting_gear_options"]["fighter"] if p["id"] == "heavy")
    items = " ".join(str(i).lower() for i in heavy["items"])
    assert "chain mail" in items
    assert "greatsword" in items
    assert heavy["armor"] == "chain_mail"
    assert heavy["currency"]["gp"] == 4


def test_class_starting_gold_matches_phb_2024_package_a():
    data = _yaml("dnd5e_equipment.yaml")["class_starting_gear_options"]
    expected = {
        "barbarian": 15,
        "bard": 19,
        "druid": 9,
        "monk": 11,
        "paladin": 9,
        "ranger": 7,
        "rogue": 8,
        "sorcerer": 28,
        "warlock": 15,
        "wizard": 5,
    }
    for class_id, gp in expected.items():
        assert data[class_id][0]["currency"]["gp"] == gp, class_id


def test_depths_hearts_diamonds_8_swapped():
    data = _yaml("brambletrek_depths_tables.yaml")
    hearts8 = data["hearts"]["8"]
    diamonds8 = data["diamonds"]["8"]
    assert hearts8.get("supplies") == 8
    assert "alcove" in hearts8["label"].lower()
    assert diamonds8.get("morale") == 8
    assert "friendly" in diamonds8["label"].lower()


def test_sneaker_eight_is_poisoned_blade():
    data = _yaml("brambletrek_player_tactics.yaml")
    text = data["player_tactics"]["sneaker"]["8"].lower()
    assert "poisoned blade" in text
    assert "shadow strike" not in text


def test_exhaustion_2024_penalties():
    char = Dnd5eCharacter(name="Test", speed=30, exhaustion=2)
    char.clamp()
    assert char.exhaustion_d20_penalty() == 4
    assert char.exhaustion_speed_penalty() == 10
    assert char.effective_speed() == 20
    prompt = format_for_prompt(char)
    assert "-4 to d20 tests" in prompt
    assert "-10 ft Speed" in prompt
    char.exhaustion = 6
    char.clamp()
    assert char.hp == 0
    assert "Dead" in char.conditions
    assert "dies at level 6" in format_for_prompt(char)


def test_structured_lookup_catches_two_leveled_spells():
    q = rewrite_rules_query(
        "Can I cast Healing Word as a bonus action and Fireball as my action on the same turn?"
    )
    assert "one spell" in q.lower()
    hits = lookup_curated_rules(q)
    titles = " ".join(h["title"].lower() for h in hits)
    assert "spell slot" in titles


def test_heroic_inspiration_spend():
    char = Dnd5eCharacter(name="Test", heroic_inspiration=True)
    assert char.spend_heroic_inspiration() is True
    assert char.heroic_inspiration is False
    assert char.spend_heroic_inspiration() is False
    assert char.grant_heroic_inspiration() == "granted"
    assert char.grant_heroic_inspiration() == "already_has"
