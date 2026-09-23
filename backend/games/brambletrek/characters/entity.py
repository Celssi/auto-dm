"""Brambletrek Gnawborn character sheet (stats + creation choices)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from backend.config import CURATED_DIR

TABLES_YAML = CURATED_DIR / "brambletrek_character_tables.yaml"

STAT_MAX = 20
STAT_MIN = 0


def get_legacy_options() -> dict[str, dict[str, str]]:
    from backend.games.brambletrek.dm.curated import legacy_options

    return legacy_options()


@dataclass
class BrambletrekCharacter:
    game_id: str = "brambletrek"
    id: str = ""
    name: str = ""
    reason_band: str = ""
    background_band: str = ""
    trinket_band: str = ""
    legacy: str = ""
    health: int = 10
    morale: int = 10
    supplies: int = 10
    journey_day: int = 1
    in_aldwund: bool = False
    active_adventure: str = ""
    reason_card: str = ""
    background_card: str = ""
    trinket_card: str = ""
    notes: str = ""
    legacy_abilities_used: dict[str, bool] = field(default_factory=dict)
    resource_cards: dict[str, list[str]] = field(default_factory=dict)
    oracle_relic: bool = False
    resource_base_health: int | None = None
    resource_base_morale: int | None = None
    resource_base_supplies: int | None = None

    def is_set(self) -> bool:
        return bool(
            self.name.strip()
            or self.reason_band
            or self.background_band
            or self.trinket_band
            or self.legacy
            or self.notes.strip()
            or any(v != 10 for v in (self.health, self.morale, self.supplies))
            or self.journey_day > 1
        )

    def clamp_stats(self) -> None:
        self.health = max(STAT_MIN, min(STAT_MAX, int(self.health)))
        self.morale = max(STAT_MIN, min(STAT_MAX, int(self.morale)))
        self.supplies = max(STAT_MIN, min(STAT_MAX, int(self.supplies)))
        self.journey_day = max(1, int(self.journey_day))


_tables_cache: dict[str, Any] | None = None


def load_character_tables() -> dict[str, Any]:
    global _tables_cache
    if _tables_cache is None:
        if not TABLES_YAML.exists():
            _tables_cache = {"reasons": {}, "backgrounds": {}, "trinkets": {}, "card_bands": []}
        else:
            _tables_cache = yaml.safe_load(TABLES_YAML.read_text(encoding="utf-8")) or {}
    return _tables_cache


def table_options(table_key: str) -> list[tuple[str, str]]:
    """Return (id, label) pairs for select boxes."""
    data = load_character_tables()
    rows = data.get(table_key, {}) or {}
    options: list[tuple[str, str]] = [("", "— Not set —")]
    for band_id, meta in rows.items():
        if isinstance(meta, dict):
            options.append((str(band_id), meta.get("label", str(band_id))))
    return options


def label_for_band(table_key: str, band_id: str) -> str:
    if not band_id:
        return ""
    data = load_character_tables()
    row = (data.get(table_key) or {}).get(band_id)
    if isinstance(row, dict):
        return row.get("label", band_id)
    return band_id


def label_for_card_band(band_id: str) -> str:
    """Human label for a table card-value band (Ace, 2–4, Jack, …)."""
    if not band_id:
        return ""
    for row in load_character_tables().get("card_bands") or []:
        if isinstance(row, dict) and row.get("id") == band_id:
            return str(row.get("label", band_id))
    return band_id


def character_table_band(rank_key: str) -> str:
    """Map a playing-card rank to a character table band id (rulebook pp. 12–14)."""
    if rank_key == "ace":
        return "ace"
    if rank_key in ("jack", "queen", "king"):
        return rank_key
    n = int(rank_key)
    if 2 <= n <= 4:
        return "2-4"
    if 5 <= n <= 7:
        return "5-7"
    return "8-10"


def legacy_stat_deltas(legacy_id: str) -> tuple[int, int, int]:
    """Return (health, morale, supplies) deltas from legacy YAML."""
    if not legacy_id:
        return (0, 0, 0)
    from backend.games.brambletrek.dm.curated import _legacies_data

    meta = (_legacies_data().get("legacies") or {}).get(legacy_id) or {}
    if not isinstance(meta, dict):
        return (0, 0, 0)
    return (
        int(meta.get("health_delta", 0) or 0),
        int(meta.get("morale_delta", 0) or 0),
        int(meta.get("supplies_delta", 0) or 0),
    )


def apply_legacy_stat_change(
    char: BrambletrekCharacter,
    old_legacy: str,
    new_legacy: str,
) -> None:
    """Swap legacy boost/flaw on current resource stats (rulebook p. 17)."""
    if old_legacy == new_legacy:
        return
    oh, om, os = legacy_stat_deltas(old_legacy)
    nh, nm, ns = legacy_stat_deltas(new_legacy)
    char.health = char.health - oh + nh
    char.morale = char.morale - om + nm
    char.supplies = char.supplies - os + ns
    char.legacy = new_legacy
    char.legacy_abilities_used = {}
    char.clamp_stats()


def default_character() -> BrambletrekCharacter:
    return BrambletrekCharacter()


def character_from_dict(data: dict | None) -> BrambletrekCharacter:
    if not data:
        return default_character()
    return BrambletrekCharacter(
        game_id=str(data.get("game_id", "brambletrek") or "brambletrek"),
        id=str(data.get("id", "") or ""),
        name=str(data.get("name", "") or ""),
        reason_band=str(data.get("reason_band", "") or ""),
        background_band=str(data.get("background_band", "") or ""),
        trinket_band=str(data.get("trinket_band", "") or ""),
        legacy=str(data.get("legacy", "") or ""),
        health=int(data.get("health", 10) or 10),
        morale=int(data.get("morale", 10) or 10),
        supplies=int(data.get("supplies", 10) or 10),
        journey_day=int(data.get("journey_day", 1) or 1),
        in_aldwund=bool(data.get("in_aldwund", False)),
        active_adventure=str(data.get("active_adventure", "") or ""),
        reason_card=str(data.get("reason_card", "") or ""),
        background_card=str(data.get("background_card", "") or ""),
        trinket_card=str(data.get("trinket_card", "") or ""),
        notes=str(data.get("notes", "") or ""),
        legacy_abilities_used={
            str(k): bool(v) for k, v in (data.get("legacy_abilities_used") or {}).items()
        },
        resource_cards={
            str(k): [str(c) for c in v]
            for k, v in (data.get("resource_cards") or {}).items()
            if isinstance(v, list)
        },
        resource_base_health=(
            int(data["resource_base_health"])
            if data.get("resource_base_health") is not None
            else None
        ),
        resource_base_morale=(
            int(data["resource_base_morale"])
            if data.get("resource_base_morale") is not None
            else None
        ),
        resource_base_supplies=(
            int(data["resource_base_supplies"])
            if data.get("resource_base_supplies") is not None
            else None
        ),
        oracle_relic=bool(data.get("oracle_relic", False)),
    )


def character_to_dict(char: BrambletrekCharacter) -> dict:
    char.clamp_stats()
    return {
        "game_id": char.game_id or "brambletrek",
        "id": char.id,
        "name": char.name,
        "reason_band": char.reason_band,
        "background_band": char.background_band,
        "trinket_band": char.trinket_band,
        "legacy": char.legacy,
        "health": char.health,
        "morale": char.morale,
        "supplies": char.supplies,
        "journey_day": char.journey_day,
        "in_aldwund": char.in_aldwund,
        "active_adventure": char.active_adventure,
        "reason_card": char.reason_card,
        "background_card": char.background_card,
        "trinket_card": char.trinket_card,
        "notes": char.notes,
        "legacy_abilities_used": dict(char.legacy_abilities_used),
        "resource_cards": {k: list(v) for k, v in char.resource_cards.items()},
        "resource_base_health": char.resource_base_health,
        "resource_base_morale": char.resource_base_morale,
        "resource_base_supplies": char.resource_base_supplies,
        "oracle_relic": char.oracle_relic,
    }


def format_summary(char: BrambletrekCharacter | None) -> str:
    if char is None or not char.is_set():
        return ""
    char.clamp_stats()
    name = char.name.strip() or "Gnawborn"
    legacy = get_legacy_options().get(char.legacy, {}).get("label", "")
    bits = [
        name,
        f"Day {char.journey_day}",
        f"HP {char.health}",
        f"Morale {char.morale}",
        f"Supplies {char.supplies}",
    ]
    if legacy and legacy != "— Not set —":
        bits.insert(1, legacy)
    return " · ".join(bits)


def format_for_prompt(
    char: BrambletrekCharacter | None,
    *,
    story_mode: str = "player",
    card_source: str = "virtual",
) -> str:
    if char is None or not char.is_set():
        return ""
    char.clamp_stats()
    lines = ["Current Gnawborn character (use for journey/combat/recovery answers):"]
    if char.name.strip():
        lines.append(f"- Name: {char.name.strip()}")
    if char.reason_band:
        card_note = char.reason_card or label_for_card_band(char.reason_band)
        line = f"- Reason: {label_for_band('reasons', char.reason_band)}"
        if card_note:
            line += f" ({card_note})"
        lines.append(line)
    if char.background_band:
        card_note = char.background_card or label_for_card_band(char.background_band)
        line = f"- Background: {label_for_band('backgrounds', char.background_band)}"
        if card_note:
            line += f" ({card_note})"
        lines.append(line)
    if char.trinket_band:
        card_note = char.trinket_card or label_for_card_band(char.trinket_band)
        line = f"- Trinket: {label_for_band('trinkets', char.trinket_band)}"
        if card_note:
            line += f" ({card_note})"
        lines.append(line)
    if char.legacy:
        from backend.games.brambletrek.dm.curated import (
            adventure_meta,
            legacy_abilities,
            overcome_the_odds,
        )

        leg = get_legacy_options().get(char.legacy, {})
        lines.append(
            f"- Legacy: {leg.get('label', char.legacy)} "
            f"(boost {leg.get('boost', '?')}, flaw {leg.get('flaw', '?')})"
        )
        used = char.legacy_abilities_used or {}
        for ab in legacy_abilities(char.legacy):
            status = "used" if used.get(ab["id"]) else "available"
            lines.append(f"  - {ab.get('label', ab['id'])}: {status}")
        oto = overcome_the_odds()
        oto_status = "used" if used.get(oto["id"]) else "available"
        lines.append(f"  - {oto['label']}: {oto_status}")
    lines.append(
        f"- Resources: Health {char.health}, Morale {char.morale}, "
        f"Supplies {char.supplies} (each 0–{STAT_MAX}; at 0 roll recovery table)"
    )
    lines.append(f"- Journey day: {char.journey_day}")
    if char.in_aldwund:
        lines.append("- Location: Aldwund (Depths) — use depths journey table (pp. 26–27)")
    if char.active_adventure:
        adv = adventure_meta(char.active_adventure)
        lines.append(
            f"- Active adventure: {adv.get('label', char.active_adventure)} "
            f"(prefer this module's PDF when answering scene questions)"
        )
    if char.notes.strip():
        lines.append(f"- Notes: {char.notes.strip()}")
    lines.append(
        f"- Story mode: {story_mode} (player = facilitator only; ai_narrator = add narrative)"
    )
    lines.append(
        f"- Card source: {card_source} (physical = user reports cards; virtual = app draws)"
    )
    lines.append("When suggesting stat changes from events, apply them to these current values.")
    return "\n".join(lines)
