from backend.dm.lonelog import format_mechanical, format_narrative
from backend.dm.prose_style import sanitize_narration_dashes


def test_sanitize_em_dash_to_comma():
    text = "Salthollow sprawls like a wound — a city of crooked timber."
    assert "—" not in sanitize_narration_dashes(text)
    assert (
        "Salthollow sprawls like a wound, a city of crooked timber."
        in sanitize_narration_dashes(text)
    )


def test_sanitize_preserves_numeric_range():
    assert sanitize_narration_dashes("Stand 10–15 feet back.") == "Stand 10-15 feet back."


def test_sanitize_double_hyphen():
    assert "—" not in sanitize_narration_dashes(
        "The gate -- little more than timber -- blocked the path."
    )


def test_lonelog_formatters_strip_em_dashes():
    mechanical = format_mechanical("Combat begins — a hungry wolf.")
    narrative = format_narrative("The gate — little more than timber — blocked the path.")
    assert "—" not in mechanical
    assert "—" not in narrative
    assert "Combat begins, a hungry wolf." in mechanical
    assert "=> The gate, little more than timber, blocked the path." in narrative
