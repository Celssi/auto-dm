"""Brambletrek Lonelog formatters."""

from __future__ import annotations

from backend.dm.lonelog import format_mechanical, format_narrative
from backend.games.brambletrek.characters.entity import BrambletrekCharacter
from backend.games.brambletrek.dm.curated import adventure_meta
from backend.storage import append_session_log, get_session_lonelog


def card_short_label(card: str) -> str:
    parts = card.split(" of ", 1)
    if len(parts) == 2:
        rank, suit = parts
        return f"{rank[0].upper()}{suit[0].upper()}"
    return card[:3]


def format_pc(name: str, *fields: str) -> str:
    inner = "|".join(fields)
    return f"[PC:{name}|{inner}]"


def format_scene(day: int, context: str) -> str:
    return f"[Scene:Day {day}|{context}]"


def format_resources(health: int, morale: int, supplies: int, *, name: str = "") -> str:
    return format_pc(
        name.strip() or "Gnawborn",
        f"Health {health}",
        f"Morale {morale}",
        f"Supplies {supplies}",
    )


def format_scene_header(char: BrambletrekCharacter, location_hint: str = "") -> str:
    loc = location_hint.strip()
    if not loc:
        if char.in_aldwund:
            loc = "Aldwund Depths"
        elif char.active_adventure:
            adv = adventure_meta(char.active_adventure)
            loc = adv.get("label", char.active_adventure)
        else:
            loc = "Hyhill surface"
    return format_scene(char.journey_day, f"{loc}, day {char.journey_day}")


def log_to_session(session_id: str, line: str) -> None:
    if session_id and line.strip():
        append_session_log(session_id, line)


def log_draw(session_id: str, cards: list[str], *, label: str = "Drew") -> None:
    listed = ", ".join(card_short_label(c) for c in cards)
    log_to_session(session_id, format_mechanical(f"{label}: {listed} ({', '.join(cards)})"))


def log_mechanical(session_id: str, text: str) -> None:
    log_to_session(session_id, format_mechanical(text))


def log_narrative_line(session_id: str, text: str) -> None:
    log_to_session(session_id, format_narrative(text))


def recent_context(session_id: str, n_lines: int = 40) -> str:
    content = get_session_lonelog(session_id)
    lines = content.splitlines()
    tail = lines[-n_lines:] if len(lines) > n_lines else lines
    return "\n".join(tail)
