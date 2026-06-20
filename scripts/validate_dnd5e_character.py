#!/usr/bin/env python3
"""Validate D&D 5e character creation curated data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.characters.character_builder import (
    compute_spell_slots,
    level_up,
    rebuild_character,
    spell_limits,
)
from backend.characters.character_data import (
    character_options_payload,
    get_background,
    get_class,
    get_species,
    list_backgrounds,
    list_classes,
    list_species,
)
from backend.characters.entity import Dnd5eCharacter
from backend.characters.multiclass import class_levels_dict


def main() -> int:
    assert len(list_classes(include_faerun=False)) == 12
    assert len(list_species()) == 10
    assert len(list_backgrounds(include_faerun=False)) == 16
    faerun_bgs = list_backgrounds(include_faerun=True)
    assert len(faerun_bgs) > 16
    assert get_background("harper") is not None
    bard = get_class("bard")
    assert "College of the Moon" in bard.get("subclasses", [])
    assert get_class("wizard")["hit_die"] == 6
    assert get_species("elf")["speed"] == 30
    assert get_background("acolyte")["feat"] == "Magic Initiate (Cleric)"

    caster_expectations = {
        "bard": {"mode": "prepared", "cantrips": 2, "picks": 4, "slots": {"1": 2}, "ability": "cha"},
        "cleric": {"mode": "prepared", "cantrips": 3, "picks": 4, "slots": {"1": 2}, "ability": "wis"},
        "druid": {"mode": "prepared", "cantrips": 2, "picks": 4, "slots": {"1": 2}, "ability": "wis"},
        "wizard": {"mode": "prepared", "cantrips": 3, "picks": 4, "slots": {"1": 2}, "ability": "int"},
        "sorcerer": {"mode": "prepared", "cantrips": 4, "picks": 2, "slots": {"1": 2}, "ability": "cha"},
        "warlock": {"mode": "pact", "cantrips": 2, "picks": 2, "slots": {"1": 1}, "ability": "cha"},
        "paladin": {"mode": "prepared", "cantrips": 0, "picks": 4, "slots": {"1": 2}, "ability": "cha"},
        "ranger": {"mode": "prepared", "cantrips": 0, "picks": 4, "slots": {"1": 2}, "ability": "wis"},
    }
    for cid, exp in caster_expectations.items():
        cls = get_class(cid)
        assert cls is not None
        assert cls.get("spellcasting") == exp["mode"], cid
        scores = {k: 10 for k in ("str", "dex", "con", "int", "wis", "cha")}
        scores[exp["ability"]] = 16  # +3 modifier
        char = Dnd5eCharacter(class_name=cid, level=1, ability_scores=scores)
        lim = spell_limits(char)
        assert lim["cantrips"] == exp["cantrips"], (cid, lim)
        pick_key = "known" if exp["mode"] in ("known", "pact") else "prepared"
        assert lim[pick_key] == exp["picks"], (cid, lim)
        slots = compute_spell_slots(char)
        assert slots == exp["slots"], (cid, slots)

    for cid in ("barbarian", "fighter", "monk", "rogue"):
        char = Dnd5eCharacter(class_name=cid, level=1)
        assert spell_limits(char) == {"cantrips": 0, "prepared": 0, "known": 0}
        assert compute_spell_slots(char) == {}

    opts = character_options_payload(include_faerun=False)
    assert "classes" in opts and "spell_lists" in opts
    assert opts.get("faerun") is None

    faerun_opts = character_options_payload(include_faerun=True)
    assert faerun_opts.get("faerun_available") is True
    assert len(faerun_opts["backgrounds"]) > len(opts["backgrounds"])

    char = Dnd5eCharacter(
        name="Test",
        species="human",
        class_name="wizard",
        background="sage",
        level=1,
        class_skill_choices=["arcana", "history"],
        cantrips=["fire bolt", "light"],
        prepared_spells=["magic missile", "shield"],
        ability_scores_set=True,
    )
    char = rebuild_character(char, recompute_hp=True)
    assert char.max_hp >= 1
    assert char.spell_slots.get("1", 0) >= 2

    leveled = level_up(rebuild_character(Dnd5eCharacter(name="X", class_name="fighter", level=1)))
    assert leveled.level == 2

    mc = Dnd5eCharacter(
        name="Multi",
        classes=[
            {"class_name": "fighter", "level": 2, "subclass": "", "class_skill_choices": []},
            {"class_name": "wizard", "level": 1, "subclass": "", "class_skill_choices": ["arcana"]},
        ],
    )
    mc = rebuild_character(mc, recompute_hp=True)
    assert mc.level == 3
    assert len(class_levels_dict(mc)) == 2

    from backend.characters.features import subclass_features_for, unlocked_features

    feats = subclass_features_for("barbarian", "Path of the Berserker", 3)
    assert "Frenzy" in feats
    unlocked = unlocked_features(
        rebuild_character(
            Dnd5eCharacter(
                name="Barb",
                classes=[
                    {
                        "class_name": "barbarian",
                        "level": 3,
                        "subclass": "Path of the Berserker",
                        "class_skill_choices": [],
                    }
                ],
            )
        )
    )
    assert unlocked["subclass_features"]

    print("All D&D 5e character validation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
