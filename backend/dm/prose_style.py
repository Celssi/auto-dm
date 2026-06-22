"""Player-facing prose style helpers."""

from __future__ import annotations

import re

_EM_DASH = "\u2014"
_EN_DASH = "\u2013"

NARRATION_STYLE_RULES = """Style (mandatory for all player-facing prose):
- Never use em dashes (—) or en dashes (–) as punctuation or clause breaks.
- Do not join sentences or insert asides with — or –; use commas, semicolons, periods, or parentheses.
- Hyphen-minus (-) is only for compound words and numeric ranges (e.g. 10-15 feet, well known).
- This rule applies to narration, NPC dialogue, and scene descriptions shown to the player."""


def sanitize_narration_dashes(text: str) -> str:
    """Replace em/en dashes used as punctuation with commas; keep numeric ranges."""
    if not text:
        return text

    out = text
    out = re.sub(rf"(\d)\s*{_EN_DASH}\s*(\d)", r"\1-\2", out)
    out = re.sub(rf"(\d)\s*{_EM_DASH}\s*(\d)", r"\1-\2", out)
    out = re.sub(rf"\s*{_EM_DASH}\s*", ", ", out)
    out = re.sub(rf"\s*{_EN_DASH}\s*(?!\d)", ", ", out)
    out = re.sub(r"\s*--\s*", ", ", out)
    out = re.sub(r",\s*,+", ", ", out)
    out = re.sub(r",\s+\.", ".", out)
    out = re.sub(r"\.\s*,", ".", out)
    return out.strip()
