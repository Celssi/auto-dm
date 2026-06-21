from backend.games.dnd5e.characters.entity import character_from_dict, character_to_dict


def test_appearance_round_trips_via_equipment_notes():
    char = character_from_dict({"name": "Test", "appearance": "Tall human with a scar."})
    assert char.equipment_notes == "Tall human with a scar."

    data = character_to_dict(char)
    assert data["equipment_notes"] == "Tall human with a scar."
    assert data["appearance"] == "Tall human with a scar."


def test_equipment_notes_preferred_over_appearance():
    char = character_from_dict(
        {
            "equipment_notes": "Stored notes",
            "appearance": "Draft notes",
        }
    )
    assert char.equipment_notes == "Stored notes"
