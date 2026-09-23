"""Load curated Brambletrek YAML tables and resolve card lookups."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR
from backend.games.brambletrek.characters.entity import BrambletrekCharacter

_RANK_ALIASES = {
    "a": "ace",
    "ace": "ace",
    "j": "jack",
    "jack": "jack",
    "q": "queen",
    "queen": "queen",
    "k": "king",
    "king": "king",
}

_CARD_RE = re.compile(
    r"^\s*(?P<rank>[2-9]|10|[ajqk]|ace|jack|queen|king)\s+of\s+(?P<suit>hearts|diamonds|clubs|spades)\s*$",
    re.IGNORECASE,
)


def _load_yaml(name: str) -> dict[str, Any]:
    path = CURATED_DIR / name
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _journey_tables() -> dict[str, Any]:
    return _load_yaml("brambletrek_journey_tables.yaml")


@lru_cache(maxsize=1)
def _depths_tables() -> dict[str, Any]:
    return _load_yaml("brambletrek_depths_tables.yaml")


@lru_cache(maxsize=1)
def _recovery_tables() -> dict[str, Any]:
    return _load_yaml("brambletrek_recovery_tables.yaml")


@lru_cache(maxsize=1)
def _items_table() -> dict[str, Any]:
    return _load_yaml("brambletrek_items.yaml")


@lru_cache(maxsize=1)
def _combat_reference() -> dict[str, Any]:
    return _load_yaml("brambletrek_combat_reference.yaml")


@lru_cache(maxsize=1)
def _player_tactics() -> dict[str, Any]:
    return _load_yaml("brambletrek_player_tactics.yaml")


@lru_cache(maxsize=1)
def _legacies_data() -> dict[str, Any]:
    return _load_yaml("brambletrek_legacies.yaml")


@lru_cache(maxsize=1)
def _reason_endings_data() -> dict[str, Any]:
    return _load_yaml("brambletrek_reason_endings.yaml")


@lru_cache(maxsize=1)
def _character_tables_data() -> dict[str, Any]:
    return _load_yaml("brambletrek_character_tables.yaml")


_CHARACTER_TABLE_KEYS = {
    "reason": ("reasons", "Reason for adventure", "p. 12"),
    "background": ("backgrounds", "Background", "p. 13"),
    "trinket": ("trinkets", "Trinket", "p. 14"),
}


@lru_cache(maxsize=1)
def _adventures_data() -> dict[str, Any]:
    return _load_yaml("brambletrek_adventures.yaml")


def adventure_options() -> list[tuple[str, str]]:
    """(id, label) for active adventure select."""
    rows = _adventures_data().get("adventures") or {}
    return [
        (str(adv_id), (meta or {}).get("label", str(adv_id)))
        for adv_id, meta in rows.items()
        if isinstance(meta, dict)
    ]


def adventure_meta(adventure_id: str) -> dict[str, Any]:
    if not adventure_id:
        return (_adventures_data().get("adventures") or {}).get("", {}) or {}
    return (_adventures_data().get("adventures") or {}).get(adventure_id) or {}


def complete_edition_label() -> str:
    return str(
        _adventures_data().get("complete_edition_label") or "Brambletrek Complete Digital Edition"
    )


def lookup_reason_ending(reason_band: str) -> dict[str, Any] | None:
    if not reason_band:
        return None
    row = (_reason_endings_data().get("endings") or {}).get(reason_band)
    if not isinstance(row, dict):
        return None
    return dict(row)


def lookup_character_table(table: str, band: str) -> dict[str, Any] | None:
    if not table or not band:
        return None
    mapping = _CHARACTER_TABLE_KEYS.get(table)
    if not mapping:
        return None
    yaml_key, _, _ = mapping
    row = (_character_tables_data().get(yaml_key) or {}).get(band)
    if not isinstance(row, dict):
        return None
    return dict(row)


def format_character_table(
    table: str,
    band: str,
    *,
    card: str = "",
    adventure_id: str = "",
) -> str:
    """Markdown block for a Reason / Background / Trinket row (Core Rulebook pp. 12–14)."""
    if table == "reason" and adventure_id:
        from backend.games.brambletrek.modules.loader import format_module_reason, module_reasons

        if module_reasons(adventure_id) and card:
            text = format_module_reason(adventure_id, card)
            if text:
                return text
    mapping = _CHARACTER_TABLE_KEYS.get(table)
    row = lookup_character_table(table, band)
    if not mapping or not row:
        return ""
    _, table_label, page = mapping
    title = str(row.get("title") or row.get("label") or band).strip()
    body = str(row.get("body", "")).strip()
    header = f"**{title}**"
    if card:
        header += f" — _{card}_"
    parts = [f"**{table_label}** (Core Rulebook {page}):", header]
    if body:
        parts.append(body)
    return "\n\n".join(parts)


def format_reason_ending(reason_band: str, *, reason_label: str = "") -> str:
    """Markdown block for Reason ending (p. 36)."""
    row = lookup_reason_ending(reason_band)
    if not row:
        band_note = reason_label or reason_band or "not set"
        return (
            f"**Reason ending** — set your Reason for adventure on the character sheet "
            f"(current: {band_note}). Endings are on Core Rulebook p. 36."
        )
    intro = (_reason_endings_data().get("intro") or "").strip()
    title = row.get("title", reason_band)
    body = str(row.get("body", "")).strip()
    header = f"**{title}**"
    if reason_label:
        header += f" _(Reason: {reason_label})_"
    parts = ["**Curated Reason ending** (Core Rulebook p. 36):", header, body]
    if intro:
        parts.insert(1, intro)
    parts.append("_Choose a true ending or one that lets you stay in Hyhill and continue later._")
    return "\n\n".join(p for p in parts if p)


def format_adventure_context(adventure_id: str) -> str:
    meta = adventure_meta(adventure_id)
    if not adventure_id or not meta:
        return ""
    lines = [
        f"Active adventure module: **{meta.get('label', adventure_id)}**",
        "_Scenes and tables come from the indexed adventure PDF (RAG), not curated journey YAML._",
    ]
    syn = str(meta.get("synopsis", "")).strip()
    if syn:
        lines.append(syn)
    acts = meta.get("acts") or []
    if acts:
        lines.append("Structure: " + " → ".join(str(a) for a in acts))
    tips = meta.get("tips") or []
    if tips:
        lines.append("Tips: " + " ".join(str(t) for t in tips))
    return "\n".join(lines)


def parse_playing_card(card: str) -> dict[str, Any] | None:
    """Parse '9 of spades' into suit, rank_key, numeric_value."""
    m = _CARD_RE.match(card.strip())
    if not m:
        return None
    raw_rank = m.group("rank").lower()
    rank_key = _RANK_ALIASES.get(raw_rank, raw_rank)
    suit = m.group("suit").lower()
    if rank_key == "ace":
        numeric = 11
    elif rank_key in ("jack", "queen", "king"):
        numeric = 10
    else:
        numeric = int(rank_key)
    return {"suit": suit, "rank_key": rank_key, "numeric_value": numeric, "card": card.strip()}


def recovery_band(rank_key: str) -> str:
    if rank_key in ("jack", "queen"):
        return "jack-queen"
    if rank_key in ("king", "ace"):
        return "king-ace"
    n = int(rank_key)
    if 2 <= n <= 4:
        return "2-4"
    if 5 <= n <= 7:
        return "5-7"
    return "8-10"


def lookup_journey_event(
    card: str,
    *,
    in_depths: bool = False,
    adventure_id: str = "",
) -> dict[str, Any] | None:
    if adventure_id and not in_depths:
        from backend.games.brambletrek.modules.loader import (
            lookup_module_journey_event,
            module_journey_tables,
        )

        if module_journey_tables(adventure_id):
            return lookup_module_journey_event(adventure_id, card, in_depths=False)
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    suit = parsed["suit"]
    rank_key = parsed["rank_key"]
    tables = _depths_tables() if in_depths else _journey_tables()
    row = (tables.get(suit) or {}).get(rank_key)
    if not isinstance(row, dict):
        return None
    zone = "aldwund" if in_depths else "surface"
    return {**row, "suit": suit, "rank_key": rank_key, "card": parsed["card"], "zone": zone}


def _apply_journey_tags(char: BrambletrekCharacter, event: dict[str, Any]) -> None:
    tags = event.get("tags") or []
    if "depths" in tags:
        char.in_aldwund = True
    if "exit" in tags:
        char.in_aldwund = False


def lookup_recovery(stat: str, card: str) -> dict[str, Any] | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    band = recovery_band(parsed["rank_key"])
    row = (_recovery_tables().get(stat) or {}).get(band)
    if not isinstance(row, dict):
        return None
    return {**row, "stat": stat, "band": band, "card": parsed["card"]}


def lookup_item(card: str) -> dict[str, Any] | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    row = (_items_table().get("items") or {}).get(parsed["rank_key"])
    if not isinstance(row, dict):
        return None
    return {**row, "card": parsed["card"]}


def event_needs_item_draw(event: dict[str, Any] | None) -> bool:
    return bool(event and "item" in (event.get("tags") or []))


def item_effect_preview(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, icon in (("health", "Health"), ("morale", "Morale"), ("supplies", "Supplies")):
        val = item.get(key)
        if val is not None and val != 0:
            sign = "+" if int(val) > 0 else ""
            parts.append(f"{icon} {sign}{val}")
    note = item.get("note")
    if note:
        parts.append(str(note))
    return ", ".join(parts) if parts else "One-time use — keep until spent"


def format_item_draw(card: str) -> str:
    row = lookup_item(card)
    if not row:
        return f"**Item** — {card}: _no curated row_"
    preview = item_effect_preview(row)
    return f"**Item** — {card}: **{row.get('label', '?')}** ({preview})"


def apply_item_effects(char: BrambletrekCharacter, item: dict[str, Any]) -> str:
    """Apply immediate stat bonuses from a found item."""
    before = (char.health, char.morale, char.supplies)
    apply_event_deltas(char, item)
    char.clamp_stats()
    after = (char.health, char.morale, char.supplies)
    changes = [
        f"{name} {b}→{a}"
        for name, b, a in zip(("Health", "Morale", "Supplies"), before, after)
        if b != a
    ]
    return ", ".join(changes) if changes else "No immediate stat change"


def legacy_abilities(legacy_id: str) -> list[dict[str, Any]]:
    if not legacy_id:
        return []
    meta = (_legacies_data().get("legacies") or {}).get(legacy_id) or {}
    rows = meta.get("abilities") or []
    return [dict(r) for r in rows if isinstance(r, dict)]


def overcome_the_odds() -> dict[str, str]:
    row = _legacies_data().get("overcome_the_odds") or {}
    return {
        "id": "overcome_the_odds",
        "label": row.get("label", "Overcome the Odds"),
        "description": str(row.get("description", "")).strip(),
    }


def reset_daily_legacy_abilities(char: BrambletrekCharacter) -> None:
    char.legacy_abilities_used = {}


def legacy_options() -> dict[str, dict[str, str]]:
    """UI select options: id -> {label, boost, flaw, ability}."""
    data = _legacies_data().get("legacies") or {}
    options: dict[str, dict[str, str]] = {
        "": {"label": "— Not set —", "boost": "", "flaw": "", "ability": ""},
    }
    for leg_id, meta in data.items():
        if isinstance(meta, dict):
            abilities = legacy_abilities(str(leg_id))
            summary = abilities[0]["label"] if abilities else ""
            if len(abilities) > 1:
                summary = f"{len(abilities)} daily abilities"
            options[str(leg_id)] = {
                "label": meta.get("label", str(leg_id)),
                "boost": meta.get("boost", ""),
                "flaw": meta.get("flaw", ""),
                "ability": summary,
            }
    return options


def legacy_by_roll(total: int) -> str:
    ids = [k for k in (_legacies_data().get("legacies") or {}) if k]
    if not ids:
        return "Seer"
    meta = (_legacies_data().get("legacies") or {}).get(ids[(total - 1) % len(ids)], {})
    return meta.get("label", ids[(total - 1) % len(ids)]) if isinstance(meta, dict) else ids[0]


def legacy_id_by_roll(total: int) -> str:
    ids = [k for k in (_legacies_data().get("legacies") or {}) if k]
    if not ids:
        return "seer"
    return ids[(total - 1) % len(ids)]


def _stat_line(event: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, icon in (("health", "Health"), ("morale", "Morale"), ("supplies", "Supplies")):
        val = event.get(key)
        if val is not None and val != 0:
            sign = "+" if int(val) > 0 else ""
            parts.append(f"{icon} {sign}{val}")
    if event.get("all_stats") is not None:
        v = int(event["all_stats"])
        sign = "+" if v > 0 else ""
        parts.append(f"All stats {sign}{v}")
    if event.get("combat"):
        parts.append("**Combat**")
    tags = event.get("tags") or []
    if "depths" in tags:
        parts.append("(DEPTHS)")
    if "item" in tags:
        parts.append("(ITEM)")
    if "exit" in tags:
        parts.append("(EXIT)")
    note = event.get("note")
    if note:
        parts.append(f"_{note}_")
    return ", ".join(parts) if parts else "—"


def format_journey_events(
    cards: list[str],
    labels: list[str] | None = None,
    *,
    in_aldwund: bool = False,
    adventure_id: str = "",
) -> str:
    if adventure_id and not in_aldwund:
        from backend.games.brambletrek.modules.loader import (
            format_module_journey_events,
            module_journey_tables,
        )

        if module_journey_tables(adventure_id):
            return format_module_journey_events(adventure_id, cards, labels)
    labels = labels or [f"Event {i + 1}" for i in range(len(cards))]
    in_depths = in_aldwund
    lines = [
        "**Curated Aldwund depths** (Core Rulebook pp. 26–27):"
        if in_depths
        else "**Curated journey events** (Core Rulebook pp. 24–25):"
    ]
    for label, card in zip(labels, cards):
        event = lookup_journey_event(card, in_depths=in_depths, adventure_id=adventure_id)
        if not event:
            lines.append(f"- **{label}** ({card}): _no curated row_")
            continue
        stats = _stat_line(event)
        zone = "depths" if in_depths else "surface"
        lines.append(f"- **{label}** — {card} [{zone}]: **{event.get('label', '?')}** ({stats})")
        tags = event.get("tags") or []
        if "depths" in tags:
            in_depths = True
        if "exit" in tags:
            in_depths = False
    return "\n".join(lines)


def apply_event_deltas(char: BrambletrekCharacter, event: dict[str, Any]) -> None:
    for key in ("health", "morale", "supplies"):
        delta = event.get(key)
        if delta is not None:
            setattr(char, key, getattr(char, key) + int(delta))
    all_delta = event.get("all_stats")
    if all_delta is not None:
        d = int(all_delta)
        char.health += d
        char.morale += d
        char.supplies += d
    char.clamp_stats()


def journey_depths_trace(
    cards: list[str],
    *,
    start_in_aldwund: bool,
    adventure_id: str = "",
) -> list[bool]:
    """For each card, whether Aldwund depths table applies at resolution time."""
    in_depths = start_in_aldwund
    trace: list[bool] = []
    for card in cards:
        trace.append(in_depths)
        event = lookup_journey_event(card, in_depths=in_depths, adventure_id=adventure_id)
        if event:
            tags = event.get("tags") or []
            if "depths" in tags:
                in_depths = True
            if "exit" in tags:
                in_depths = False
    return trace


def apply_single_journey_event(
    char: BrambletrekCharacter,
    card: str,
    *,
    in_depths: bool | None = None,
    adventure_id: str = "",
) -> str:
    """Apply one journey/depths event when the player resolves it."""
    if in_depths is None:
        in_depths = char.in_aldwund
    before = (char.health, char.morale, char.supplies)
    event = lookup_journey_event(card, in_depths=in_depths, adventure_id=adventure_id)
    if not event:
        return f"{card}: no curated row found."

    notes: list[str] = []
    if event.get("combat"):
        notes.append("Combat — resolve with **Combat setup** (no automatic stat change).")
    else:
        apply_event_deltas(char, event)
        stat = _stat_line(event)
        if stat != "—":
            notes.append(stat)

    _apply_journey_tags(char, event)
    char.clamp_stats()
    after = (char.health, char.morale, char.supplies)
    if not event.get("combat"):
        notes.append(
            f"Health {before[0]}→{after[0]}, "
            f"Morale {before[1]}→{after[1]}, Supplies {before[2]}→{after[2]}"
        )
    if char.in_aldwund and not in_depths:
        notes.append("Entered Aldwund (Depths).")
    elif not char.in_aldwund and in_depths:
        notes.append("Returned to surface.")
    return f"**{event.get('label', card)}** — " + "; ".join(notes)


def apply_journey_to_character(
    char: BrambletrekCharacter,
    cards: list[str],
    *,
    increment_day: bool = True,
    skip_combat: bool = False,
    adventure_id: str = "",
) -> str:
    """Apply all events at once (quick shortcut only — not rules-accurate mid-day)."""
    before = (char.health, char.morale, char.supplies)
    trace = journey_depths_trace(cards, start_in_aldwund=char.in_aldwund, adventure_id=adventure_id)
    for card, in_depths in zip(cards, trace):
        event = lookup_journey_event(card, in_depths=in_depths, adventure_id=adventure_id)
        if not event:
            continue
        if skip_combat and event.get("combat"):
            _apply_journey_tags(char, event)
            continue
        apply_event_deltas(char, event)
        _apply_journey_tags(char, event)
    if increment_day:
        char.journey_day = max(1, char.journey_day + 1)
        reset_daily_legacy_abilities(char)
    char.clamp_stats()
    after = (char.health, char.morale, char.supplies)
    loc = "Aldwund" if char.in_aldwund else "surface"
    mode = " (non-combat only)" if skip_combat else ""
    return (
        f"Bulk apply{mode}: Health {before[0]}→{after[0]}, "
        f"Morale {before[1]}→{after[1]}, Supplies {before[2]}→{after[2]}"
        + (f"; journey day **{char.journey_day}**" if increment_day else "")
        + f"; location **{loc}**"
    )


def format_recovery_draw(stat: str, card: str) -> str:
    row = lookup_recovery(stat, card)
    if not row:
        return f"**{stat.title()} recovery** — {card}: _no curated row_"
    return (
        f"**{stat.title()} recovery** — {card} (band {row.get('band', '?')}): "
        f"**{row.get('label', '?')}**"
    )


def lookup_opponent_tactic(card: str) -> dict[str, Any] | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    row = (_combat_reference().get("opponent_tactics") or {}).get(parsed["rank_key"])
    if not isinstance(row, dict):
        return None
    return {**row, "rank_key": parsed["rank_key"], "card": parsed["card"]}


def lookup_player_tactic(legacy_id: str, card: str) -> dict[str, Any] | None:
    if not legacy_id:
        return None
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    row = (_player_tactics().get("player_tactics") or {}).get(legacy_id, {}).get(parsed["rank_key"])
    if not row:
        return None
    return {
        "legacy": legacy_id,
        "rank_key": parsed["rank_key"],
        "card": parsed["card"],
        "effect": str(row),
    }


def format_opponent_tactics_table() -> str:
    rows = _combat_reference().get("opponent_tactics") or {}
    if not rows:
        return ""
    lines = ["**Opponent Tactics** (curated, p. 30):"]
    for rank, meta in rows.items():
        if isinstance(meta, dict):
            lines.append(f"- {rank}: {meta.get('label', '?')}")
    return "\n".join(lines)


def _initiative_value(card: str) -> int | None:
    parsed = parse_playing_card(card)
    if not parsed:
        return None
    return int(parsed["numeric_value"])


def format_combat_setup_curated(
    cards: list[str],
    *,
    legacy_id: str = "",
    legacy_label: str = "",
    adventure_id: str = "",
    combat_context: dict | None = None,
) -> str:
    """Curated combat setup: initiative, opponent info, tactic hand effects."""
    from backend.games.brambletrek.modules.combat import (
        format_module_combat_setup,
        uses_module_combat,
    )

    adv = adventure_id or str((combat_context or {}).get("adventure_id") or "")
    if combat_context or (adv and uses_module_combat(adv)):
        module_text = format_module_combat_setup(
            cards,
            legacy_id=legacy_id,
            legacy_label=legacy_label,
            adventure_id=adv,
            combat_context=combat_context,
        )
        if module_text:
            return module_text

    if len(cards) < 6:
        return ""
    your_init, opp_init = cards[0], cards[1]
    tactic_cards = cards[2:6]
    lines = ["**Curated combat setup** (Core Rulebook pp. 30–31):"]

    yv, ov = _initiative_value(your_init), _initiative_value(opp_init)
    if yv is not None and ov is not None:
        if yv > ov:
            first = "You"
        elif ov > yv:
            first = "Opponent"
        else:
            first = "Tie — redraw or house rule"
        lines.append(
            f"- Initiative: you {your_init} ({yv}) vs opponent {opp_init} ({ov}) — **{first}** goes first."
        )

    opp_parsed = parse_playing_card(opp_init)
    if opp_parsed:
        suits = _combat_reference().get("opponent_type_by_suit") or {}
        opp_type = suits.get(opp_parsed["suit"], "")
        if opp_type:
            lines.append(f"- Opponent type (by suit): {opp_parsed['suit']} → {opp_type}.")
        hp_map = _combat_reference().get("opponent_health_by_rank") or {}
        rk = opp_parsed["rank_key"]
        if rk in hp_map:
            lines.append(f"- Opponent HP if rank is {rk}: {hp_map[rk]}.")

    leg = legacy_label or legacy_id or "your Legacy"
    lines.append(f"- Your tactic hand ({leg}):")
    for i, card in enumerate(tactic_cards, 1):
        tactic = lookup_player_tactic(legacy_id, card)
        if tactic:
            lines.append(f"  - Tactic {i} ({card}): {tactic['effect']}")
        else:
            lines.append(f"  - Tactic {i} ({card}): set Legacy to resolve tactic table.")

    lines.append("")
    lines.append(format_opponent_tactics_table())
    rules = _combat_reference().get("rules") or {}
    for key in ("initiative", "tactics", "opponent_tactics"):
        if rules.get(key):
            lines.append(f"- {rules[key]}")
    return "\n".join(lines)


def combat_reference_summary() -> str:
    data = _combat_reference()
    if not data:
        return ""
    lines = ["**Combat reference** (curated):"]
    hp = data.get("opponent_health_by_rank") or {}
    if hp:
        lines.append("- Opponent HP by rank: " + ", ".join(f"{k}={v}" for k, v in hp.items()))
    suits = data.get("opponent_type_by_suit") or {}
    if suits:
        lines.append("- Opponent type by suit: " + ", ".join(f"{s}={t}" for s, t in suits.items()))
    rules = data.get("rules") or {}
    for key in ("initiative", "tactics", "opponent_tactics"):
        if rules.get(key):
            lines.append(f"- {rules[key]}")
    table = format_opponent_tactics_table()
    if table:
        lines.append("")
        lines.append(table)
    return "\n".join(lines)
