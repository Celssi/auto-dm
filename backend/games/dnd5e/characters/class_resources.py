"""Fighter resources, AC breakdown, and equipment helpers (PHB 2024)."""

from __future__ import annotations

from typing import Any

from backend.games.dnd5e.characters.character_data import get_armor, get_weapon, shield_ac_bonus
from backend.games.dnd5e.characters.entity import Dnd5eCharacter
from backend.games.dnd5e.characters.multiclass import class_levels_dict

# Fighter table: Second Wind uses at levels 1 / 4 / 10.
_SECOND_WIND_BY_FIGHTER_LEVEL = (
    (10, 4),
    (4, 3),
    (1, 2),
)


def _norm_item(name: str) -> str:
    return str(name or "").strip().lower().replace("'", "").replace("_", " ").replace("-", " ")


def fighter_level(char: Dnd5eCharacter) -> int:
    return int(class_levels_dict(char).get("fighter", 0) or 0)


def second_wind_max(char: Dnd5eCharacter) -> int:
    level = fighter_level(char)
    for threshold, uses in _SECOND_WIND_BY_FIGHTER_LEVEL:
        if level >= threshold:
            return uses
    return 0


def sync_second_wind_uses(char: Dnd5eCharacter) -> None:
    mx = second_wind_max(char)
    remaining = int(getattr(char, "second_wind_remaining", -1) or -1)
    if mx <= 0:
        char.second_wind_remaining = 0
        return
    if remaining < 0:
        char.second_wind_remaining = mx
    else:
        char.second_wind_remaining = max(0, min(mx, remaining))


def recover_second_wind_short_rest(char: Dnd5eCharacter) -> str | None:
    mx = second_wind_max(char)
    if mx <= 0:
        return None
    before = int(char.second_wind_remaining or 0)
    char.second_wind_remaining = min(mx, before + 1)
    if char.second_wind_remaining == before:
        return None
    return f"Second Wind {before}→{char.second_wind_remaining}/{mx}"


def recover_second_wind_long_rest(char: Dnd5eCharacter) -> None:
    mx = second_wind_max(char)
    char.second_wind_remaining = mx


def spend_second_wind(char: Dnd5eCharacter) -> bool:
    sync_second_wind_uses(char)
    if second_wind_max(char) <= 0 or int(char.second_wind_remaining or 0) <= 0:
        return False
    char.second_wind_remaining = int(char.second_wind_remaining) - 1
    return True


def compute_ac_details(char: Dnd5eCharacter) -> dict[str, Any]:
    """PHB 2024 AC: armor table + DEX + shield + Defense fighting style."""
    dex = char.ability_modifier("dex")
    armor_id = str(char.armor or "none").strip().lower() or "none"
    armor = get_armor(armor_id) if armor_id != "none" else None
    parts: list[dict[str, Any]] = []
    if not armor:
        computed = 10 + dex
        parts.append({"label": "Unarmored", "value": 10})
        if dex:
            parts.append({"label": "Dexterity", "value": dex})
    else:
        computed = int(armor.get("base_ac", 10) or 10)
        label = str(armor.get("label") or armor_id).replace("_", " ")
        parts.append({"label": label, "value": computed})
        category = str(armor.get("category", "") or "")
        if armor.get("add_dex") or category == "light":
            computed += dex
            if dex:
                parts.append({"label": "Dexterity", "value": dex})
        elif "dex_cap" in armor or category == "medium":
            cap = int(armor.get("dex_cap", 2) or 2)
            added = min(dex, cap)
            computed += added
            if added:
                parts.append({"label": f"Dexterity (max +{cap})", "value": added})
        # heavy armor adds no DEX
        if str(char.fighting_style_feat or "").strip().lower() == "defense" and category in (
            "light",
            "medium",
            "heavy",
        ):
            computed += 1
            parts.append({"label": "Defense", "value": 1})
    if char.shield:
        bonus = shield_ac_bonus()
        computed += bonus
        parts.append({"label": "Shield", "value": bonus})
    computed = max(1, min(30, computed))
    formula = " + ".join(f"{p['label']} {p['value']}" for p in parts) if parts else str(computed)
    shown = int(char.ac or computed) if char.ac_manual else computed
    return {
        "computed": computed,
        "ac": shown,
        "manual": bool(char.ac_manual),
        "parts": parts,
        "formula": f"{formula} = {computed}",
        "armor_id": armor_id,
        "shield": bool(char.shield),
    }


def owned_weapon_keys(char: Dnd5eCharacter) -> set[str]:
    keys: set[str] = set()
    for weapon in char.weapons or []:
        if not isinstance(weapon, dict):
            continue
        raw = str(weapon.get("name") or "")
        key = _norm_item(raw)
        if key:
            keys.add(key)
            row = get_weapon(raw.lower().replace(" ", "_"))
            if row:
                keys.add(_norm_item(str(row.get("id") or "")))
                keys.add(_norm_item(str(row.get("label") or "")))
    for item in char.inventory or []:
        key = _norm_item(str(item))
        if key:
            keys.add(key)
    return keys


def weapon_mastery_warnings(char: Dnd5eCharacter) -> list[dict[str, str]]:
    """Mastery weapons that do not appear in weapons or inventory."""
    owned = owned_weapon_keys(char)
    warnings: list[dict[str, str]] = []
    for raw in char.weapon_mastery or []:
        wid = str(raw or "").strip()
        if not wid:
            continue
        key = _norm_item(wid)
        row = get_weapon(wid.lower().replace(" ", "_"))
        label = str((row or {}).get("label") or wid).replace("_", " ")
        aliases = {key, _norm_item(label)}
        if row:
            aliases.add(_norm_item(str(row.get("id") or "")))
        if aliases.isdisjoint(owned):
            warnings.append(
                {
                    "weapon": wid,
                    "label": label,
                    "message": (
                        f"Weapon Mastery includes {label}, but this character does not "
                        "currently own that weapon. You can still keep the mastery "
                        "(fighters may change one choice after a Long Rest)."
                    ),
                }
            )
    return warnings


def equipment_display_items(char: Dnd5eCharacter) -> list[str]:
    """Worn armor, shield, weapons, then other inventory, without duplicates."""
    seen: set[str] = set()
    items: list[str] = []

    def add(label: str) -> None:
        text = str(label or "").strip()
        key = _norm_item(text)
        if not text or key in seen or key in {"none", "unarmored"}:
            return
        seen.add(key)
        items.append(text)

    armor = get_armor(str(char.armor or "none"))
    if armor and str(armor.get("id") or "") not in ("", "none"):
        add(str(armor.get("label") or char.armor))
    if char.shield:
        add("Shield")
    for weapon in char.weapons or []:
        if isinstance(weapon, dict):
            add(str(weapon.get("name") or ""))
    for item in char.inventory or []:
        add(str(item))
    return items
