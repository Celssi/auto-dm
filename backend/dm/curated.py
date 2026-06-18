"""D&D 5e solo oracle curated table."""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR

_ORACLE_PATH = CURATED_DIR / "dnd5e_oracle.yaml"


@lru_cache(maxsize=1)
def _answers() -> dict[str, Any]:
    with _ORACLE_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("answers") or {}


def lookup_oracle(roll: int) -> dict[str, str]:
    answers = _answers()
    entry = answers.get(str(roll)) if isinstance(answers, dict) else None
    if not isinstance(entry, dict):
        return {"answer": "unknown", "twist": "", "text": ""}
    answer = str(entry.get("answer", "") or "")
    twist = str(entry.get("twist", "") or "")
    text = answer
    if twist:
        text = f"{answer}, {twist}"
    return {"answer": answer, "twist": twist, "text": text}


def roll_oracle() -> dict[str, Any]:
    roll = random.randint(1, 6)
    row = lookup_oracle(roll)
    summary = f"Solo oracle d6 = **{roll}** — **{row['text']}**"
    return {"roll": roll, **row, "summary": summary}
