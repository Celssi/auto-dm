"""Level-up preview and prepared spell limits."""

from __future__ import annotations

from backend.characters.character_builder import level_up_preview, rebuild_character, spell_limits_for_class
from backend.characters.entity import Dnd5eCharacter


def _druid(**kwargs) -> Dnd5eCharacter:
    base = dict(
        name="Test",
        class_name="druid",
        level=3,
        ability_scores={"str": 8, "dex": 16, "con": 15, "int": 12, "wis": 17, "cha": 10},
        ability_scores_set=True,
        cantrips=["Druidcraft", "Produce Flame"],
        prepared_spells=["Entangle", "Goodberry", "Faerie Fire", "Detect Magic", "Healing Word", "Speak with Animals"],
        classes=[{"class_name": "druid", "level": 3, "subclass": "Circle of the Moon", "class_skill_choices": []}],
    )
    base.update(kwargs)
    return rebuild_character(Dnd5eCharacter(**base))


def test_druid_prepared_uses_wis_and_level():
    char = _druid()
    lim = spell_limits_for_class(char, "druid", class_level=3)
    assert lim["prepared"] == 6  # WIS +3 + level 3
    assert lim["cantrips"] == 2


def test_druid_level_4_preview_cantrip_and_slots():
    char = _druid()
    preview = level_up_preview(char, class_name="druid")
    assert preview["can_level"] is True
    assert preview["total_level_after"] == 4
    assert preview["class_cantrips"]["limit_after"] == 3
    assert preview["class_cantrips"]["limit_increased"] is True
    assert preview["class_cantrips"]["additional_picks"] == 1
    assert preview["spells"]["limit_after"] == 7
    assert preview["asi_this_level"] is True
    assert any("cantrip" in n.lower() for n in preview["notices"])
    assert any("Ability Score" in n for n in preview["notices"])


def test_over_limit_cantrips_no_forced_drop():
    char = _druid(cantrips=["A", "B", "C"])
    preview = level_up_preview(char, class_name="druid")
    assert preview["class_cantrips"]["current"] == 3
    assert preview["class_cantrips"]["additional_picks"] == 0
    assert preview["class_cantrips"]["limit_increased"] is True


def test_subclass_reminder_at_level_3():
    char = rebuild_character(
        Dnd5eCharacter(
            name="X",
            class_name="druid",
            level=2,
            classes=[{"class_name": "druid", "level": 2, "subclass": "", "class_skill_choices": []}],
        )
    )
    preview = level_up_preview(char, class_name="druid")
    assert preview["needs_subclass"] is True
    assert any("subclass" in n.lower() for n in preview["notices"])
