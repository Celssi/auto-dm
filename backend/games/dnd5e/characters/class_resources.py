"""Fighter resources, AC breakdown, and equipment helpers (PHB 2024)."""

from __future__ import annotations

import re
from typing import Any

from backend.games.dnd5e.characters.character_data import (
    get_armor,
    get_weapon,
    list_weapons,
    shield_ac_bonus,
)
from backend.games.dnd5e.characters.entity import Dnd5eCharacter
from backend.games.dnd5e.characters.multiclass import class_levels_dict

_ITEM_QTY_RE = re.compile(r"^(.*?)\s*\((\d+)\)\s*$")
_ALL_MASTER_CLASSES = frozenset({"barbarian", "fighter", "paladin", "ranger"})
_ROGUE_MASTER_CLASSES = frozenset({"rogue"})

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


def paladin_level(char: Dnd5eCharacter) -> int:
    return int(class_levels_dict(char).get("paladin", 0) or 0)


def rogue_level(char: Dnd5eCharacter) -> int:
    return int(class_levels_dict(char).get("rogue", 0) or 0)


def lay_on_hands_max(char: Dnd5eCharacter) -> int:
    level = paladin_level(char)
    return 5 * level if level > 0 else 0


def sync_lay_on_hands(char: Dnd5eCharacter) -> None:
    mx = lay_on_hands_max(char)
    remaining = int(getattr(char, "lay_on_hands_remaining", -1) or -1)
    if mx <= 0:
        char.lay_on_hands_remaining = 0
        return
    if remaining < 0:
        char.lay_on_hands_remaining = mx
    else:
        char.lay_on_hands_remaining = max(0, min(mx, remaining))


def recover_lay_on_hands_long_rest(char: Dnd5eCharacter) -> None:
    char.lay_on_hands_remaining = lay_on_hands_max(char)


def sneak_attack_dice(char: Dnd5eCharacter) -> int:
    level = rogue_level(char)
    if level <= 0:
        return 0
    return (level + 1) // 2


def spend_second_wind(char: Dnd5eCharacter) -> bool:
    sync_second_wind_uses(char)
    if second_wind_max(char) <= 0 or int(char.second_wind_remaining or 0) <= 0:
        return False
    char.second_wind_remaining = int(char.second_wind_remaining) - 1
    return True


def compute_ac_details(char: Dnd5eCharacter) -> dict[str, Any]:
    """PHB 2024 AC: armor table + DEX + shield + Defense fighting style + Mage Armor."""
    dex = char.ability_modifier("dex")
    armor_id = str(char.armor or "none").strip().lower() or "none"
    armor = get_armor(armor_id) if armor_id != "none" else None
    parts: list[dict[str, Any]] = []
    from backend.games.dnd5e.characters.spell_resources import mage_armor_active

    unarmored = not armor
    if unarmored and mage_armor_active(char):
        computed = 13 + dex
        parts.append({"label": "Mage Armor", "value": 13})
        if dex:
            parts.append({"label": "Dexterity", "value": dex})
    elif not armor:
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
                        "(you may change mastery choices after a Long Rest)."
                    ),
                }
            )
    return warnings


def _item_base_and_qty(label: str) -> tuple[str, int]:
    text = str(label or "").strip()
    match = _ITEM_QTY_RE.match(text)
    if match:
        return match.group(1).strip(), max(1, int(match.group(2)))
    return text, 1


def _item_stack_key(name: str) -> str:
    base = _norm_item(name)
    if base.endswith("ses"):
        return base
    if base.endswith("s") and not base.endswith("ss"):
        return base[:-1]
    return base


def format_counted_item(name: str, qty: int) -> str:
    text = str(name or "").strip()
    if qty <= 1:
        return text
    return f"{text} ({qty})"


def merge_counted_labels(existing: list[str], incoming: list[str]) -> list[str]:
    counts: dict[str, tuple[str, int]] = {}
    order: list[str] = []
    for raw in list(existing or []) + list(incoming or []):
        name, qty = _item_base_and_qty(raw)
        key = _item_stack_key(name)
        if not key or key in {"none", "unarmored"}:
            continue
        if key in counts:
            display, current = counts[key]
            counts[key] = (display, current + qty)
        else:
            counts[key] = (name, qty)
            order.append(key)
    return [format_counted_item(counts[key][0], counts[key][1]) for key in order]


def class_has_weapon_mastery(class_id: str) -> bool:
    cid = str(class_id or "").strip().lower()
    return cid in _ALL_MASTER_CLASSES or cid in _ROGUE_MASTER_CLASSES


def weapon_proficient_for_class(class_id: str, weapon: dict[str, Any]) -> bool:
    cid = str(class_id or "").strip().lower()
    category = str(weapon.get("category") or "").strip().lower()
    props = {str(p).strip().lower() for p in (weapon.get("properties") or [])}
    if cid in _ALL_MASTER_CLASSES:
        return category in {"simple", "martial"}
    if cid == "rogue":
        if category == "simple":
            return True
        return category == "martial" and ("finesse" in props or "light" in props)
    if cid in {"bard", "cleric", "druid", "monk", "sorcerer", "warlock", "wizard"}:
        return category == "simple"
    return False


def mastery_weapons_for_class(class_id: str) -> list[dict[str, Any]]:
    if not class_has_weapon_mastery(class_id):
        return []
    out: list[dict[str, Any]] = []
    for row in list_weapons():
        if not isinstance(row, dict) or not row.get("id"):
            continue
        if weapon_proficient_for_class(class_id, row):
            out.append({"id": row.get("id"), "label": row.get("label") or row.get("id")})
    return out


def _armor_alias_keys(char: Dnd5eCharacter) -> set[str]:
    armor = get_armor(str(char.armor or "none"))
    keys: set[str] = set()
    if not armor or str(armor.get("id") or "") in ("", "none"):
        return keys
    label = str(armor.get("label") or char.armor)
    armor_id = str(armor.get("id") or "")
    for raw in (label, armor_id, f"{label} armor", f"{armor_id} armor"):
        keys.add(_item_stack_key(raw))
        keys.add(_norm_item(raw))
    return keys


def equipment_display_items(char: Dnd5eCharacter) -> list[str]:
    """Worn armor, shield, unique weapons, then stacked inventory without duplicates."""
    items: list[str] = []
    seen: set[str] = set()
    armor_keys = _armor_alias_keys(char)

    def add(label: str, *, skip_keys: set[str] | None = None) -> None:
        name, qty = _item_base_and_qty(label)
        key = _item_stack_key(name)
        if not name or key in {"none", "unarmored"}:
            return
        if skip_keys and (key in skip_keys or _norm_item(name) in skip_keys):
            return
        if key in seen:
            return
        seen.add(key)
        items.append(format_counted_item(name, qty))

    armor = get_armor(str(char.armor or "none"))
    if armor and str(armor.get("id") or "") not in ("", "none"):
        add(str(armor.get("label") or char.armor))
    if char.shield:
        add("Shield")

    inventory_keys = {_item_stack_key(str(item)) for item in (char.inventory or [])}
    for weapon in char.weapons or []:
        if not isinstance(weapon, dict):
            continue
        name = str(weapon.get("name") or "")
        if _item_stack_key(name) in inventory_keys:
            continue
        add(name)
    for item in char.inventory or []:
        add(str(item), skip_keys=armor_keys)
    return items


def character_has_weapon_mastery(char: Dnd5eCharacter) -> bool:
    for entry in char.normalized_class_entries():
        if class_has_weapon_mastery(str(entry.get("class_name") or "")):
            return True
    return class_has_weapon_mastery(char.class_name)


def weapon_attack_details(char: Dnd5eCharacter) -> list[dict[str, Any]]:
    """Computed attack bonus and damage for each owned weapon."""
    pb = char.proficiency_bonus()
    mastery_ids = {_norm_item(str(w)) for w in (char.weapon_mastery or [])}
    has_mastery = character_has_weapon_mastery(char)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for weapon in char.weapons or []:
        if not isinstance(weapon, dict):
            continue
        name = str(weapon.get("name") or "").strip()
        key = _norm_item(name)
        if not name or key in seen:
            continue
        seen.add(key)
        catalog = get_weapon(name.lower().replace(" ", "_")) or {}
        ability = str(weapon.get("ability") or catalog.get("ability") or "str").lower()
        props = {str(p).lower() for p in (catalog.get("properties") or [])}
        if "finesse" in props:
            str_mod = char.ability_modifier("str")
            dex_mod = char.ability_modifier("dex")
            ability = "dex" if dex_mod >= str_mod else "str"
        elif str(catalog.get("category") or "").lower() == "ranged" or "ammunition" in props:
            ability = "dex"
        mod = char.ability_modifier(ability)
        class_id = str(char.class_name or "")
        proficient = weapon_proficient_for_class(class_id, catalog or weapon) or bool(
            weapon.get("proficient")
        )
        atk = mod + (pb if proficient else 0)
        damage = str(weapon.get("damage") or catalog.get("damage") or "1d6")
        dmg_type = str(weapon.get("damage_type") or catalog.get("damage_type") or "")
        dmg_mod = f"{mod:+d}" if mod else "+0"
        mastery_id = _norm_item(str(catalog.get("id") or name))
        mastery_name = str(catalog.get("mastery") or "").strip()
        uses_mastery = bool(has_mastery and mastery_name and mastery_id in mastery_ids)
        versatile = "versatile" in props
        extra = ""
        if versatile:
            extra = " (versatile 1d8)" if damage == "1d6" else " (versatile)"
        line = f"{atk:+d} to hit, {damage}{dmg_mod} {dmg_type}{extra}"
        if uses_mastery:
            line += f", mastery {mastery_name.title()}"
        rows.append(
            {
                "name": name,
                "attack": atk,
                "damage": damage,
                "damage_mod": mod,
                "damage_type": dmg_type,
                "ability": ability,
                "proficient": proficient,
                "mastery": mastery_name if uses_mastery else "",
                "line": line,
            }
        )
    return rows
