"""Spell autocomplete and cast confirmation tests."""

from __future__ import annotations

from backend.games.dnd5e.characters.entity import character_from_dict
from backend.games.dnd5e.dm.spell_autocomplete import (
    confirmation_message,
    extract_cast_query,
    resolve_spell_query,
)


def _druid(**overrides):
    base = {
        "class_name": "druid",
        "level": 3,
        "cantrips": ["druidcraft"],
        "prepared_spells": ["healing word", "moonbeam", "entangle"],
        "classes": [{"class_name": "druid", "level": 3}],
    }
    base.update(overrides)
    return character_from_dict(base)


def test_extract_cast_query_i_cast():
    assert extract_cast_query("I cast moonspell at the goblin") == "moonspell"
    assert extract_cast_query("cast healing word") == "healing word"
    assert extract_cast_query("/cast Moonbeam") == "Moonbeam"


def test_fuzzy_match_moonspell_to_moonbeam():
    char = _druid()
    res = resolve_spell_query(char, "moonspell")
    assert res.status == "fuzzy"
    assert res.spell_name.lower() == "moonbeam"


def test_exact_match_moonbeam():
    char = _druid()
    res = resolve_spell_query(char, "moonbeam")
    assert res.status == "exact"
    assert res.spell_name.lower() == "moonbeam"


def test_confirmation_message():
    char = _druid()
    res = resolve_spell_query(char, "moonspell")
    msg = confirmation_message(res)
    assert "moonspell" in msg
    assert "Moonbeam" in msg or "moonbeam" in msg
