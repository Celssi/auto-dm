"""Third-caster subclass spellcasting (Eldritch Knight, Arcane Trickster)."""

from backend.games.dnd5e.characters.character_builder import compute_spell_slots, rebuild_character, spell_limits
from backend.games.dnd5e.characters.creation_choices import apply_creation_choices
from backend.games.dnd5e.characters.entity import Dnd5eCharacter
from backend.games.dnd5e.characters.spell_resources import is_spell_available, spell_level_for


def _fighter_ek(level: int = 3) -> Dnd5eCharacter:
    return Dnd5eCharacter(
        name="EK",
        species="human",
        class_name="fighter",
        level=level,
        subclass="Eldritch Knight",
        classes=[{"class_name": "fighter", "level": level, "subclass": "Eldritch Knight"}],
        ability_scores={"str": 15, "dex": 12, "con": 14, "int": 14, "wis": 10, "cha": 8},
        ability_scores_set=True,
        cantrips=["fire_bolt", "mending"],
        prepared_spells=["shield", "magic_missile", "burning_hands"],
    )


def test_fighter_3_ek_spell_slots():
    char = rebuild_character(_fighter_ek(3))
    assert compute_spell_slots(char) == {"1": 2}


def test_fighter_4_ek_spell_slots():
    char = rebuild_character(_fighter_ek(4))
    assert compute_spell_slots(char) == {"1": 3}


def test_ek_spell_limits_level_3():
    char = rebuild_character(_fighter_ek(3))
    limits = spell_limits(char)
    assert limits["cantrips"] == 2
    assert limits["prepared"] == 3


def test_ek_wizard_spell_list():
    char = rebuild_character(_fighter_ek(3))
    assert spell_level_for(char, "Fire Bolt") == 0
    assert is_spell_available(char, "shield")


def test_apply_third_caster_creation_choices():
    char = Dnd5eCharacter(
        name="EK",
        species="human",
        class_name="fighter",
        level=3,
        feature_choices={
            "subclass": "eldritch_knight",
            "third_caster_cantrips": ["fire_bolt", "mending"],
            "third_caster_spells": ["shield", "magic_missile", "burning_hands"],
        },
        classes=[{"class_name": "fighter", "level": 3, "subclass": "Eldritch Knight"}],
    )
    apply_creation_choices(char)
    assert char.subclass == "Eldritch Knight"
    assert "fire_bolt" in char.cantrips
    assert "shield" in char.prepared_spells
