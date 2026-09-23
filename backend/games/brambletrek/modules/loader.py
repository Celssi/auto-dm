"""Load per-adventure curated Brambletrek module tables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from backend.config import CURATED_DIR

MODULES_DIR = CURATED_DIR / "brambletrek_modules"
INDEX_FILE = MODULES_DIR / "index.yaml"

JOURNEY_SUITS = ("hearts", "diamonds", "clubs", "spades")
JOURNEY_RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace")
REASON_RANKS = JOURNEY_RANKS


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def module_index() -> dict[str, Any]:
    return _load_yaml(INDEX_FILE)


def module_ids() -> list[str]:
    rows = module_index().get("modules") or {}
    return [str(k) for k in rows if k]


def module_file(adventure_id: str) -> Path | None:
    if not adventure_id:
        return None
    entry = (module_index().get("modules") or {}).get(adventure_id)
    if not isinstance(entry, dict):
        return None
    rel = str(entry.get("file") or "").strip()
    if not rel:
        return None
    return MODULES_DIR / rel


@lru_cache(maxsize=32)
def load_module(adventure_id: str) -> dict[str, Any]:
    if not adventure_id:
        return {}
    path = module_file(adventure_id)
    if not path:
        return {}
    data = _load_yaml(path)
    if not data:
        return {}
    return {**data, "id": adventure_id}


def module_play_config(adventure_id: str) -> dict[str, Any]:
    mod = load_module(adventure_id)
    play = mod.get("play") if isinstance(mod.get("play"), dict) else {}
    return {
        "journey_cards_per_day": int(play.get("journey_cards_per_day") or 4),
        "use_core_depths": bool(play.get("use_core_depths", True)),
        "use_core_combat": bool(play.get("use_core_combat", True)),
        "reason_key": str(play.get("reason_key") or "band"),
        "default_scene_table": str(play.get("default_scene_table") or ""),
    }


def module_journey_tables(adventure_id: str) -> dict[str, Any] | None:
    mod = load_module(adventure_id)
    journeys = mod.get("journeys")
    if not isinstance(journeys, dict) or not journeys:
        return None
    return journeys


def module_reasons(adventure_id: str) -> dict[str, Any] | None:
    mod = load_module(adventure_id)
    reasons = mod.get("reasons")
    if not isinstance(reasons, dict) or not reasons:
        return None
    return reasons


def module_scene_tables(adventure_id: str) -> dict[str, Any]:
    mod = load_module(adventure_id)
    tables = mod.get("scene_tables")
    return dict(tables) if isinstance(tables, dict) else {}


def module_exploration_tables(adventure_id: str) -> dict[str, Any]:
    mod = load_module(adventure_id)
    tables = mod.get("exploration_tables")
    return dict(tables) if isinstance(tables, dict) else {}


def module_path_locations(adventure_id: str) -> dict[str, Any]:
    mod = load_module(adventure_id)
    rows = mod.get("path_locations")
    return dict(rows) if isinstance(rows, dict) else {}


def lookup_module_journey_event(
    adventure_id: str,
    card: str,
    *,
    in_depths: bool = False,
) -> dict[str, Any] | None:
    """Resolve a card against module journey tables (module play ignores Aldwund unless configured)."""
    from backend.games.brambletrek.dm.curated import parse_playing_card

    if in_depths and module_play_config(adventure_id).get("use_core_depths"):
        from backend.games.brambletrek.dm.curated import lookup_journey_event

        return lookup_journey_event(card, in_depths=True)

    parsed = parse_playing_card(card)
    if not parsed:
        return None
    tables = module_journey_tables(adventure_id)
    if not tables:
        return None
    row = (tables.get(parsed["suit"]) or {}).get(parsed["rank_key"])
    if not isinstance(row, dict):
        return None
    return {
        **row,
        "suit": parsed["suit"],
        "rank_key": parsed["rank_key"],
        "card": parsed["card"],
        "zone": "module",
    }


def lookup_module_scene_row(adventure_id: str, table_id: str, card: str) -> dict[str, Any] | None:
    from backend.games.brambletrek.dm.curated import parse_playing_card

    parsed = parse_playing_card(card)
    if not parsed:
        return None
    table = module_scene_tables(adventure_id).get(table_id)
    if not isinstance(table, dict):
        return None
    # Suit-split tables (festival events) or flat rank tables
    if parsed["suit"] in table:
        suit_row = table[parsed["suit"]]
        if isinstance(suit_row, dict):
            if parsed["rank_key"] in suit_row:
                row = suit_row[parsed["rank_key"]]
            elif "label" in suit_row or "scene_table" in suit_row:
                row = suit_row
            else:
                row = None
        else:
            row = None
    else:
        row = table.get(parsed["rank_key"])
    if not isinstance(row, dict):
        return None
    return {**row, "card": parsed["card"], "table": table_id}


def lookup_module_exploration_row(
    adventure_id: str, table_id: str, card: str
) -> dict[str, Any] | None:
    from backend.games.brambletrek.dm.curated import parse_playing_card

    parsed = parse_playing_card(card)
    if not parsed:
        return None
    table = module_exploration_tables(adventure_id).get(table_id)
    if not isinstance(table, dict):
        return None
    row = table.get(parsed["rank_key"])
    if not isinstance(row, dict):
        return None
    return {**row, "card": parsed["card"], "table": table_id}


def lookup_module_reason(adventure_id: str, card: str) -> dict[str, Any] | None:
    from backend.games.brambletrek.characters.entity import character_table_band
    from backend.games.brambletrek.dm.curated import parse_playing_card

    reasons = module_reasons(adventure_id)
    if not reasons:
        return None
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    cfg = module_play_config(adventure_id)
    key = (
        parsed["rank_key"]
        if cfg["reason_key"] == "rank"
        else character_table_band(parsed["rank_key"])
    )
    row = reasons.get(key)
    if not isinstance(row, dict):
        return None
    return {**row, "card": parsed["card"], "band": key}


def format_module_reason(adventure_id: str, card: str) -> str:
    row = lookup_module_reason(adventure_id, card)
    if not row:
        return ""
    mod = load_module(adventure_id)
    title = str(row.get("title") or row.get("label") or "").strip()
    body = str(row.get("body") or row.get("label") or "").strip()
    label = mod.get("label") or adventure_id
    parts = [f"**Reason for adventure** ({label}):", f"**{title}** — _{card}_"]
    if body and body != title:
        parts.append(body)
    return "\n\n".join(parts)


def format_module_journey_events(
    adventure_id: str,
    cards: list[str],
    labels: list[str] | None = None,
) -> str:
    from backend.games.brambletrek.dm.curated import _stat_line as journey_event_stat_preview

    mod = load_module(adventure_id)
    labels = labels or [f"Event {i + 1}" for i in range(len(cards))]
    header = str(
        mod.get("journey_heading") or f"**{mod.get('label', adventure_id)}** — exploration events"
    )
    lines = [header]
    for label, card in zip(labels, cards):
        event = lookup_module_journey_event(adventure_id, card)
        if not event:
            lines.append(f"- **{label}** ({card}): _no curated row_")
            continue
        stats = journey_event_stat_preview(event)
        lines.append(f"- **{label}** — {card}: **{event.get('label', '?')}** ({stats})")
    return "\n".join(lines)


def format_module_scene_draw(
    adventure_id: str,
    table_id: str,
    card: str,
    *,
    label: str = "Scene",
) -> str:
    from backend.games.brambletrek.dm.curated import _stat_line as journey_event_stat_preview

    row = lookup_module_scene_row(adventure_id, table_id, card)
    if not row:
        return f"- **{label}** ({card}): _no curated row_"
    stats = journey_event_stat_preview(row)
    body = str(row.get("body") or "").strip()
    line = f"- **{label}** — {card}: **{row.get('label', '?')}** ({stats})"
    if body:
        line += f"\n  {body}"
    return line


def format_module_exploration_draw(
    adventure_id: str,
    table_id: str,
    card: str,
    *,
    label: str = "Event",
) -> str:
    from backend.games.brambletrek.dm.curated import _stat_line as journey_event_stat_preview

    row = lookup_module_exploration_row(adventure_id, table_id, card)
    if not row:
        return f"- **{label}** ({card}): _no curated row_"
    stats = journey_event_stat_preview(row)
    return f"- **{label}** — {card}: **{row.get('label', '?')}** ({stats})"


def format_adventure_scene(
    adventure_id: str,
    route_cards: list[str],
    activity_cards: list[str] | None = None,
    *,
    scene_table: str = "",
) -> str:
    """Format curated adventure draws (journey, scene tables, or exploration)."""
    mod = load_module(adventure_id)
    if module_journey_tables(adventure_id):
        labels = [f"Event {i + 1}" for i in range(len(route_cards))]
        return format_module_journey_events(adventure_id, route_cards, labels)

    play = module_play_config(adventure_id)
    table_id = scene_table or play.get("default_scene_table") or ""
    exploration = module_exploration_tables(adventure_id)
    if table_id and exploration.get(table_id):
        lines = [
            f"**{mod.get('label', adventure_id)}** — exploration ({table_id.replace('_', ' ')})"
        ]
        for i, card in enumerate(route_cards):
            lines.append(
                format_module_exploration_draw(adventure_id, table_id, card, label=f"Event {i + 1}")
            )
        return "\n".join(lines)

    scenes = module_scene_tables(adventure_id)
    if (
        scenes.get("choose_adventure")
        and activity_cards
        and len(activity_cards) == len(route_cards)
    ):
        lines = [f"**{mod.get('label', adventure_id)}** — festival activities"]
        for i, (route_card, act_card) in enumerate(zip(route_cards, activity_cards)):
            route = lookup_module_scene_row(adventure_id, "choose_adventure", route_card)
            sub_table = str((route or {}).get("scene_table") or "")
            route_label = (route or {}).get("label") or "Activity"
            lines.append(
                f"- **Activity {i + 1}** — route {route_card}: **{route_label}** → table `{sub_table}`"
            )
            if sub_table:
                lines.append(
                    "  "
                    + format_module_scene_draw(
                        adventure_id,
                        sub_table,
                        act_card,
                        label=f"Result {i + 1}",
                    ).lstrip("- ")
                )
        return "\n".join(lines)

    if table_id and scenes.get(table_id):
        lines = [f"**{mod.get('label', adventure_id)}** — {table_id.replace('_', ' ')}"]
        for i, card in enumerate(route_cards):
            lines.append(
                format_module_scene_draw(adventure_id, table_id, card, label=f"Draw {i + 1}")
            )
        return "\n".join(lines)

    return ""


def journey_cards_for_adventure(adventure_id: str, *, in_aldwund: bool = False) -> int:
    if in_aldwund or not adventure_id:
        return 4
    return int(module_play_config(adventure_id).get("journey_cards_per_day") or 4)


def module_has_curated_tables(adventure_id: str) -> bool:
    if not adventure_id:
        return False
    mod = load_module(adventure_id)
    if not mod:
        return False
    return bool(
        module_journey_tables(adventure_id)
        or module_scene_tables(adventure_id)
        or module_exploration_tables(adventure_id)
    )
