"""Apply PHB 2024 rules when building or leveling a D&D 5e character."""

from __future__ import annotations

import random
from typing import Any

from backend.games.dnd5e.characters.character_data import (
    full_caster_slots,
    get_armor,
    get_background,
    get_class,
    get_species,
    half_caster_slots,
    shield_ac_bonus,
    skills_data,
    spell_list_for,
)
from backend.games.dnd5e.characters.entity import (
    ABILITY_KEYS,
    Dnd5eCharacter,
    character_from_dict,
    character_to_dict,
)
from backend.games.dnd5e.characters.features import unlocked_features
from backend.games.dnd5e.characters.multiclass import (
    asi_feat_slots_multiclass,
    can_multiclass_into,
    class_levels_dict,
    compute_multiclass_spell_slots,
    hit_dice_pool,
    normalize_class_entries,
    primary_class_entry,
    sync_legacy_class_fields,
    total_class_level,
)
from backend.games.dnd5e.characters.spell_resources import (
    compute_wild_shape_max,
    normalize_spell_name,
    preserve_remaining_spell_slots,
    recover_pact_slots_on_short_rest,
    sync_wild_shape_uses,
)

_SPELLCASTING_FULL = {"bard", "cleric", "druid", "sorcerer", "wizard"}
_SPELLCASTING_HALF = {"paladin", "ranger"}
_SPELLCASTING_PACT = {"warlock"}
_PREPARED_BY_ABILITY = frozenset({"cleric", "druid", "wizard", "paladin", "ranger"})
_SPELLCASTING_ABILITY = {
    "cleric": "wis",
    "druid": "wis",
    "wizard": "int",
    "paladin": "cha",
    "ranger": "wis",
}


def _level_index(level: int) -> int:
    return max(0, min(19, int(level or 1) - 1))


def _by_level(table: list | None, level: int, default: int = 0) -> int:
    if not isinstance(table, list) or not table:
        return default
    return int(table[_level_index(level)] or default)


def apply_background_asi(
    scores: dict[str, int],
    background_id: str,
    *,
    plus2: str = "",
    plus1: str = "",
    all_three: bool = False,
) -> dict[str, int]:
    """Background ASI: +2/+1 to two of three abilities, or +1 to all three."""
    bg = get_background(background_id)
    if not bg:
        return dict(scores)
    out = dict(scores)
    options = [
        str(a).lower() for a in (bg.get("ability_scores") or []) if str(a).lower() in ABILITY_KEYS
    ]
    if not options:
        return out
    if all_three:
        for ab in options[:3]:
            out[ab] = min(20, out.get(ab, 8) + 1)
        return out
    p2 = plus2.lower() if plus2.lower() in options else options[0]
    remaining = [a for a in options if a != p2]
    p1 = plus1.lower() if plus1.lower() in remaining else (remaining[0] if remaining else p2)
    out[p2] = min(20, out.get(p2, 8) + 2)
    out[p1] = min(20, out.get(p1, 8) + 1)
    return out


def standard_array_for_class(class_id: str) -> dict[str, int]:
    table = skills_data().get("standard_array_by_class") or {}
    row = table.get(class_id)
    if isinstance(row, dict):
        return {k: int(row.get(k, 10) or 10) for k in ABILITY_KEYS}
    return {k: 10 for k in ABILITY_KEYS}


def compute_spell_slots(char: Dnd5eCharacter) -> dict[str, int]:
    levels = class_levels_dict(char)
    caster_classes = sum(
        1 for cid, lv in levels.items() if lv > 0 and (get_class(cid) or {}).get("spellcasting")
    )
    if len(levels) > 1 or caster_classes > 1:
        mc = compute_multiclass_spell_slots(char)
        if mc:
            return mc
    cls = get_class(char.class_name)
    if not cls or not cls.get("spellcasting"):
        return {}
    cid = char.class_name
    level = levels.get(cid, char.level)
    mode = cls.get("spellcasting")
    if mode == "pact":
        pact = cls.get("pact_slots_by_level") or []
        row = pact[_level_index(level)] if pact else {}
        if isinstance(row, dict):
            count = int(row.get("slots", 0) or 0)
            slot_level = int(row.get("level", 1) or 1)
            if count > 0:
                return {str(slot_level): count}
        return {}
    if cid in _SPELLCASTING_HALF or mode == "prepared" and cid in _SPELLCASTING_HALF:
        return half_caster_slots(level)
    if cid in _SPELLCASTING_FULL or mode in ("prepared", "known"):
        return full_caster_slots(level)
    return {}


def compute_max_hp(char: Dnd5eCharacter, *, first_level: bool = False) -> int:
    from backend.games.dnd5e.characters.origin_feats import tough_hp_bonus

    levels = class_levels_dict(char)
    if len(levels) <= 1:
        cls = get_class(char.class_name)
        hit_die = int((cls or {}).get("hit_die", 8) or 8)
        con_mod = char.ability_modifier("con")
        if char.level <= 1:
            base = max(1, hit_die + con_mod)
        else:
            per_level = max(1, (hit_die // 2) + 1 + con_mod)
            base = max(1, hit_die + con_mod + per_level * (char.level - 1))
    else:
        con_mod = char.ability_modifier("con")
        base = 0
        for cid, lv in levels.items():
            cls = get_class(cid) or {}
            hit_die = int(cls.get("hit_die", 8) or 8)
            base += max(1, hit_die + con_mod)
            if lv > 1:
                per_level = max(1, (hit_die // 2) + 1 + con_mod)
                base += per_level * (lv - 1)
        base = max(1, base)
    return max(1, base + tough_hp_bonus(char))


def _normalize_tool_proficiencies(tools: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in tools:
        label = str(raw or "").strip()
        if not label:
            continue
        key = normalize_spell_name(label)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(label.lower().replace(" ", "_"))
    return out


def merge_proficiencies(char: Dnd5eCharacter) -> tuple[list[str], list[str], list[str]]:
    """Return (skills, saves, tools) after all classes + background."""
    saves: set[str] = set()
    skills = list(char.skill_proficiencies or [])
    tools = list(char.tool_proficiencies or [])
    bg = get_background(char.background)
    for entry in normalize_class_entries(char):
        cls = get_class(entry["class_name"])
        for s in (cls or {}).get("saving_throws") or []:
            saves.add(str(s).lower())
        for sk in entry.get("class_skill_choices") or []:
            s = str(sk).lower()
            if s and s not in skills:
                skills.append(s)
    for sk in char.class_skill_choices or []:
        s = str(sk).lower()
        if s and s not in skills:
            skills.append(s)
    if bg:
        for sk in bg.get("skills") or []:
            s = str(sk).lower()
            if s and s not in skills:
                skills.append(s)
        tool = str(bg.get("tool") or "").strip()
        if tool:
            tools.append(tool)
    if char.species == "human" and char.human_skill:
        hs = str(char.human_skill).lower()
        if hs and hs not in skills:
            skills.append(hs)
    return skills, sorted(saves), _normalize_tool_proficiencies(tools)


def _prepared_spell_cap(class_id: str, class_level: int, ability_mod: int) -> int:
    """PHB 2024: ability mod + class level (half level, rounded up, for half casters)."""
    if class_id in _SPELLCASTING_HALF:
        half = (class_level + 1) // 2
        return max(1, ability_mod + half)
    return max(1, ability_mod + class_level)


def spell_limits_for_class(
    char: Dnd5eCharacter,
    class_id: str,
    *,
    class_level: int | None = None,
) -> dict[str, int]:
    cls = get_class(class_id)
    if not cls or not cls.get("spellcasting"):
        return {"cantrips": 0, "prepared": 0, "known": 0}
    level = int(
        class_level if class_level is not None else class_levels_dict(char).get(class_id, 0)
    )
    if level <= 0:
        return {"cantrips": 0, "prepared": 0, "known": 0}
    cantrips = _by_level(cls.get("cantrips_by_level"), level, 0)
    mode = cls.get("spellcasting")
    if mode in ("known", "pact"):
        known = _by_level(cls.get("spells_known_by_level"), level, 0)
        return {"cantrips": cantrips, "prepared": 0, "known": known}
    if class_id in _PREPARED_BY_ABILITY:
        ab = _SPELLCASTING_ABILITY.get(class_id, str(cls.get("primary_ability", "wis")).lower())
        prepared = _prepared_spell_cap(class_id, level, char.ability_modifier(ab))
        return {"cantrips": cantrips, "prepared": prepared, "known": 0}
    prepared = _by_level(cls.get("prepared_by_level"), level, 0)
    return {"cantrips": cantrips, "prepared": prepared, "known": 0}


def spell_limits(char: Dnd5eCharacter) -> dict[str, int]:
    totals = {"cantrips": 0, "prepared": 0, "known": 0}
    entries = normalize_class_entries(char)
    if not entries:
        entries = [{"class_name": char.class_name, "level": char.level}]
    for entry in entries:
        cid = str(entry.get("class_name") or "")
        if not cid:
            continue
        row = spell_limits_for_class(char, cid, class_level=int(entry.get("level", 0)))
        totals["cantrips"] += row["cantrips"]
        totals["prepared"] += row["prepared"]
        totals["known"] += row["known"]
    return totals


def _spell_pick_field(class_id: str) -> str:
    cls = get_class(class_id) or {}
    mode = cls.get("spellcasting")
    return "known_spells" if mode in ("known", "pact") else "prepared_spells"


def _spell_pick_label(class_id: str) -> str:
    cls = get_class(class_id) or {}
    mode = cls.get("spellcasting")
    if mode == "pact":
        return "Spells known (pact magic)"
    if mode == "known":
        return "Spells known"
    ab = _SPELLCASTING_ABILITY.get(class_id, str(cls.get("primary_ability", "wis")).upper())
    if class_id in _PREPARED_BY_ABILITY:
        if class_id in _SPELLCASTING_HALF:
            return f"Prepared spells ({ab} mod + half level)"
        return f"Prepared spells ({ab} mod + class level)"
    return "Prepared spells"


def _pick_budget(current: int, limit_before: int, limit_after: int) -> dict[str, int | bool]:
    return {
        "limit_before": limit_before,
        "limit_after": limit_after,
        "current": current,
        "limit_increased": limit_after > limit_before,
        "additional_picks": max(0, limit_after - current),
    }


# Levels that grant an Ability Score Improvement / feat. Most classes use the
# default; Fighter and Rogue get extras (PHB 2024).
_ASI_LEVELS_DEFAULT = (4, 8, 12, 16, 19)
_ASI_LEVELS_BY_CLASS = {
    "fighter": (4, 6, 8, 12, 14, 16, 19),
    "rogue": (4, 8, 10, 12, 16, 19),
}


def _simulate_class_level(char: Dnd5eCharacter, class_name: str) -> tuple[Dnd5eCharacter, int, int]:
    """Return character after gaining one level in class_name, plus old/new class levels."""
    target = class_name.strip().lower()
    char_after = character_from_dict(character_to_dict(char))
    entries = normalize_class_entries(char_after)
    old_level = 0
    new_level = 1
    found = False
    for entry in entries:
        if entry["class_name"] == target:
            old_level = int(entry["level"])
            entry["level"] = old_level + 1
            new_level = old_level + 1
            found = True
            break
    if not found:
        entries.append(
            {"class_name": target, "level": 1, "subclass": "", "class_skill_choices": []}
        )
    char_after.classes = entries
    sync_legacy_class_fields(char_after)
    return rebuild_character(char_after, recompute_hp=False), old_level, new_level


def level_up_preview(char: Dnd5eCharacter, *, class_name: str | None = None) -> dict[str, Any]:
    """Preview mechanical changes when gaining one level (does not mutate char)."""
    if total_class_level(char) >= 20:
        return {"can_level": False, "reason": "Already level 20"}
    target = (
        (class_name or (primary_class_entry(char) or {}).get("class_name") or char.class_name or "")
        .strip()
        .lower()
    )
    if not target:
        return {"can_level": False, "reason": "No class selected"}

    char_after, old_class_level, new_class_level = _simulate_class_level(char, target)
    limits_before = spell_limits(char)
    limits_after = spell_limits(char_after)
    cls = get_class(target) or {}
    cls_limits_before = spell_limits_for_class(char, target, class_level=old_class_level or 0)
    cls_limits_after = spell_limits_for_class(char_after, target, class_level=new_class_level)

    slots_before = compute_spell_slots(char)
    slots_after = compute_spell_slots(char_after)
    slot_changes: list[dict[str, Any]] = []
    for lvl in sorted({*slots_before.keys(), *slots_after.keys()}, key=int):
        before = int(slots_before.get(lvl, 0) or 0)
        after = int(slots_after.get(lvl, 0) or 0)
        if after > before:
            slot_changes.append({"level": int(lvl), "before": before, "after": after})

    pb_before = char.proficiency_bonus()
    pb_after = char_after.proficiency_bonus()
    asi_levels = _ASI_LEVELS_BY_CLASS.get(target, _ASI_LEVELS_DEFAULT)
    asi_this_level = new_class_level in asi_levels and old_class_level < new_class_level
    subclass_level = int(cls.get("subclass_level", 3) or 3)
    entry_after = next(
        (e for e in normalize_class_entries(char_after) if e["class_name"] == target), {}
    )
    needs_subclass = (
        new_class_level >= subclass_level and not str(entry_after.get("subclass") or "").strip()
    )

    ws_before = compute_wild_shape_max(char)
    ws_after = compute_wild_shape_max(char_after)

    spell_field = _spell_pick_field(target)
    spell_count = len(getattr(char, spell_field, []) or [])
    pick_key = "known" if spell_field == "known_spells" else "prepared"
    limit_before = limits_before[pick_key]
    limit_after = limits_after[pick_key]

    spell_list_raw = spell_list_for(target)
    spell_options: list[str] = []
    for key, names in spell_list_raw.items():
        if key != "cantrips":
            spell_options.extend(str(n) for n in names or [])

    notices: list[str] = []
    if pb_after > pb_before:
        notices.append(f"Proficiency bonus increases to +{pb_after}.")
    if cls_limits_after["cantrips"] > cls_limits_before["cantrips"]:
        cap = cls_limits_after["cantrips"]
        extra = max(0, cap - len(char.cantrips or []))
        if extra:
            notices.append(f"Learn {extra} more cantrip{'s' if extra != 1 else ''} (max {cap}).")
        else:
            notices.append(
                f"Cantrip limit increases to {cap} (you already know {len(char.cantrips or [])})."
            )
    if limit_after > limit_before:
        extra = max(0, limit_after - spell_count)
        label = _spell_pick_label(target)
        if extra:
            notices.append(
                f"Prepare or learn {extra} more "
                f"spell{'s' if extra != 1 else ''} "
                f"({label}; max {limit_after})."
            )
        else:
            notices.append(
                f"Spell limit increases to {limit_after} (you already have {spell_count})."
            )
    for row in slot_changes:
        if row["before"] == 0:
            notices.append(f"Gain level {row['level']} spell slots (×{row['after']}).")
        else:
            notices.append(f"Level {row['level']} spell slots increase to ×{row['after']}.")
    if asi_this_level:
        notices.append("Ability Score Improvement or feat available this level.")
    if needs_subclass:
        notices.append(f"Choose a {str(cls.get('label') or target.title())} subclass.")
    if ws_after > ws_before:
        notices.append(f"Wild Shape uses increase to {ws_after} per long rest.")

    from backend.games.dnd5e.characters.creation_choices import (
        choices_for_character,
        validate_creation_choices_at_level,
    )

    pending_choices = choices_for_character(
        char_after, target_class=target, target_level=new_class_level
    )
    missing_choices = validate_creation_choices_at_level(
        char_after, class_name=target, level=new_class_level
    )

    hit_die = int(cls.get("hit_die", 8) or 8)
    return {
        "can_level": True,
        "target_class": target,
        "target_class_label": str(cls.get("label") or target.title()),
        "class_level_before": old_class_level,
        "class_level_after": new_class_level,
        "total_level_before": char.level,
        "total_level_after": char_after.level,
        "hit_die": hit_die,
        "proficiency_bonus_before": pb_before,
        "proficiency_bonus_after": pb_after,
        "proficiency_bonus_increases": pb_after > pb_before,
        "cantrips": _pick_budget(
            len(char.cantrips or []), limits_before["cantrips"], limits_after["cantrips"]
        ),
        "class_cantrips": _pick_budget(
            len(char.cantrips or []),
            cls_limits_before["cantrips"],
            cls_limits_after["cantrips"],
        ),
        "spells": {
            **_pick_budget(spell_count, limit_before, limit_after),
            "field": spell_field,
            "label": _spell_pick_label(target),
        },
        "spell_slots": {"before": slots_before, "after": slots_after, "changes": slot_changes},
        "asi_this_level": asi_this_level,
        "needs_subclass": needs_subclass,
        "subclass_level": subclass_level,
        "wild_shape": {
            "max_before": ws_before,
            "max_after": ws_after,
            "limit_increased": ws_after > ws_before,
        },
        "spell_list": {
            "cantrips": list(spell_list_raw.get("cantrips") or []),
            "options": spell_options,
        },
        "notices": notices,
        "pending_choices": pending_choices,
        "missing_choices": missing_choices,
    }


def apply_starting_equipment(char: Dnd5eCharacter) -> Dnd5eCharacter:
    """Apply PHB class + background starting gear when inventory is empty."""
    if not char.class_name:
        return char
    from backend.games.dnd5e.characters.character_data import (
        list_background_gear_options,
        list_starting_gear_options,
    )

    if not char.inventory:
        options = list_starting_gear_options(char.class_name)
        if options:
            choice = str(char.starting_gear_choice or "").strip().lower()
            package = next((o for o in options if o.get("id") == choice), None) or options[0]
            if not char.starting_gear_choice:
                char.starting_gear_choice = str(package.get("id") or "standard")
            _apply_gear_package(char, package, replace=True)

    if char.background:
        bg_options = list_background_gear_options(char.background)
        if bg_options:
            bg_choice = str(char.background_gear_choice or "").strip().lower()
            bg_pkg = (
                next((o for o in bg_options if o.get("id") == bg_choice), None) or bg_options[0]
            )
            if not char.background_gear_choice:
                char.background_gear_choice = str(bg_pkg.get("id") or "kit")
            _apply_gear_package(char, bg_pkg, replace=False)
    return char


def _apply_gear_package(
    char: Dnd5eCharacter,
    package: dict[str, Any],
    *,
    replace: bool,
) -> None:
    items = list(package.get("items") or [])
    weapons = list(package.get("weapons") or [])
    if items:
        if replace:
            char.inventory = [str(i) for i in items]
        else:
            inv = list(char.inventory or [])
            for item in items:
                s = str(item)
                if s and s not in inv:
                    inv.append(s)
            char.inventory = inv
    if weapons:
        if replace and not char.weapons:
            char.weapons = _weapon_dicts(weapons)
        elif not replace:
            existing = {str(w.get("name", "")).lower() for w in char.weapons or []}
            for w in weapons:
                if isinstance(w, dict) and str(w.get("name", "")).lower() not in existing:
                    char.weapons = list(char.weapons or []) + _weapon_dicts([w])
    armor_id = str(package.get("armor") or "")
    if armor_id and char.armor in ("", "none"):
        char.armor = armor_id
    if package.get("shield"):
        char.shield = True
    coins = package.get("currency") or {}
    if isinstance(coins, dict):
        cur = dict(char.currency or {})
        for k in ("cp", "sp", "ep", "gp", "pp"):
            cur[k] = int(cur.get(k, 0) or 0) + int(coins.get(k, 0) or 0)
        char.currency = cur


def _weapon_dicts(weapons: list) -> list[dict[str, Any]]:
    return [
        {
            "name": str(w.get("name", "")),
            "damage": str(w.get("damage", "1d6")),
            "damage_type": str(w.get("damage_type", "")),
            "ability": str(w.get("ability", "str")),
            "proficient": True,
        }
        for w in weapons
        if isinstance(w, dict)
    ]


def rebuild_character(char: Dnd5eCharacter, *, recompute_hp: bool = False) -> Dnd5eCharacter:
    """Recompute derived stats from class, species, background, and level."""
    char.clamp()
    # Resolve the *base* (pre-background) ability scores, then derive the final
    # scores by applying the background increase exactly once. Tracking the base
    # separately keeps rebuild idempotent — without it, repeated saves would stack
    # the +2/+1 onto already-boosted scores.
    if char.class_name and not char.ability_scores_set:
        base = standard_array_for_class(char.class_name)
    elif char.base_ability_scores:
        base = {
            k: int(char.base_ability_scores.get(k, char.ability_scores.get(k, 10)) or 10)
            for k in ABILITY_KEYS
        }
    else:
        base = {k: int(char.ability_scores.get(k, 10) or 10) for k in ABILITY_KEYS}
    char.base_ability_scores = dict(base)

    final = dict(base)
    if char.background and char.background_asi_mode != "manual":
        final = apply_background_asi(
            final,
            char.background,
            plus2=char.background_asi_plus2,
            plus1=char.background_asi_plus1,
            all_three=char.background_asi_all_three,
        )
    # Apply ability score improvements taken at level-up (idempotent: summed from
    # the recorded choices, not the already-derived scores). Derive feats too.
    feat_names: list[str] = []
    for choice in char.asi_choices:
        if not isinstance(choice, dict):
            continue
        if choice.get("type") == "feat":
            name = str(choice.get("feat") or "").strip()
            if name:
                feat_names.append(name)
        else:
            for ab, amount in (choice.get("plus") or {}).items():
                if ab in ABILITY_KEYS:
                    final[ab] = min(20, final.get(ab, 10) + int(amount or 0))
    char.feats = feat_names
    char.ability_scores = final

    from backend.games.dnd5e.characters.creation_choices import (
        apply_creation_choices,
        collect_derived_feats,
        sync_feature_choice_fields,
    )

    sync_feature_choice_fields(char)
    apply_creation_choices(char)

    sp = get_species(char.species)
    if sp:
        char.speed = int(sp.get("speed", char.speed) or char.speed)
        sizes = sp.get("size_options") or ["medium"]
        if char.size not in sizes:
            char.size = str(sizes[0])
        if char.species == "human":
            char.heroic_inspiration = True  # Resourceful: gain on long rest
        fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
        if char.species == "elf" and str(fc.get("elven_lineage") or "").lower() == "wood_elf":
            char.speed = 35

    skills, saves, tools = merge_proficiencies(char)
    char.skill_proficiencies = skills
    char.save_proficiencies = saves
    char.tool_proficiencies = tools

    style_feats = collect_derived_feats(char)
    char.feats = feat_names + [f for f in style_feats if f not in feat_names]

    cls = get_class(char.class_name)
    if cls:
        char.hit_die = int(cls.get("hit_die", char.hit_die) or char.hit_die)
    char.hit_dice_max = total_class_level(char) or char.level
    if char.hit_dice_spent > char.hit_dice_max:
        char.hit_dice_spent = char.hit_dice_max

    sync_legacy_class_fields(char)
    prev_slots = dict(char.spell_slots)
    max_slots = compute_spell_slots(char)
    char.spell_slots = preserve_remaining_spell_slots(prev_slots, max_slots)
    sync_wild_shape_uses(char)

    if char.class_name:
        bg = get_background(char.background)
        if bg and not char.origin_feat:
            char.origin_feat = str(bg.get("feat") or "")

    if recompute_hp or char.max_hp <= 0:
        new_max = compute_max_hp(char)
        char.max_hp = new_max
        if char.hp <= 0 or char.hp > char.max_hp:
            char.hp = char.max_hp

    # Armor Class from worn armor + shield, unless the player set it manually.
    if not char.ac_manual:
        char.ac = compute_ac(char)
    elif char.ac <= 0:
        char.ac = 10 + char.ability_modifier("dex")

    char.clamp()
    return char


def finalize_new_character(char: Dnd5eCharacter) -> Dnd5eCharacter:
    """Full rebuild for new characters including starting equipment."""
    if not char.classes and char.class_name:
        char.classes = [
            {
                "class_name": char.class_name,
                "level": max(1, char.level),
                "subclass": char.subclass,
                "class_skill_choices": list(char.class_skill_choices or []),
            }
        ]
    char = apply_starting_equipment(char)
    char = rebuild_character(char, recompute_hp=True)
    ws_max = compute_wild_shape_max(char)
    if ws_max > 0:
        char.wild_shape_uses = ws_max
    return char


def compute_ac(char: Dnd5eCharacter) -> int:
    """AC from worn armor + shield (PHB 2024 armor table)."""
    dex = char.ability_modifier("dex")
    armor = get_armor(char.armor) if char.armor and char.armor != "none" else None
    if not armor:
        base = 10 + dex
    else:
        base = int(armor.get("base_ac", 10) or 10)
        category = str(armor.get("category", "") or "")
        if armor.get("add_dex") or category == "light":
            base += dex
        elif "dex_cap" in armor or category == "medium":
            base += min(dex, int(armor.get("dex_cap", 2) or 2))
        # heavy armor adds no DEX
    if char.shield:
        base += shield_ac_bonus()
    return max(1, min(30, base))


def level_up(
    char: Dnd5eCharacter,
    *,
    hp_roll: int | None = None,
    class_name: str | None = None,
) -> Dnd5eCharacter:
    if total_class_level(char) >= 20:
        return char
    entries = normalize_class_entries(char)
    target = (
        (class_name or (primary_class_entry(char) or {}).get("class_name") or char.class_name or "")
        .strip()
        .lower()
    )
    if not target:
        return char
    leveled_existing = False
    for entry in entries:
        if entry["class_name"] == target:
            entry["level"] = int(entry["level"]) + 1
            leveled_existing = True
            break
    if not leveled_existing:
        ok, _ = can_multiclass_into(char, target)
        if not ok and entries:
            return char
        entries.append(
            {"class_name": target, "level": 1, "subclass": "", "class_skill_choices": []}
        )
    char.classes = entries
    sync_legacy_class_fields(char)
    cls = get_class(target)
    hit_die = int((cls or {}).get("hit_die", 8) or 8)
    con_mod = char.ability_modifier("con")
    if hp_roll is None:
        hp_roll = random.randint(1, hit_die)
    gain = max(1, int(hp_roll) + con_mod)
    char.max_hp = max(1, char.max_hp + gain)
    char.hp = min(char.max_hp, char.hp + gain)
    return rebuild_character(char, recompute_hp=False)


def add_multiclass_level(char: Dnd5eCharacter, class_id: str) -> tuple[Dnd5eCharacter, str]:
    """Add first level in a new class if prerequisites met."""
    class_id = class_id.strip().lower()
    levels = class_levels_dict(char)
    if class_id in levels:
        return char, "Already has levels in that class"
    if total_class_level(char) >= 20:
        return char, "Already level 20"
    ok, reason = can_multiclass_into(char, class_id)
    if not ok:
        return char, reason or "Prerequisites not met"
    entries = normalize_class_entries(char)
    entries.append({"class_name": class_id, "level": 1, "subclass": "", "class_skill_choices": []})
    char.classes = entries
    return rebuild_character(char, recompute_hp=True), ""


def asi_feat_slots(class_id: str, level: int) -> int:
    """Number of ASI/feat choices unlocked by the given level."""
    levels = _ASI_LEVELS_BY_CLASS.get(class_id, _ASI_LEVELS_DEFAULT)
    return sum(1 for lv in levels if level >= lv)


def character_creation_summary(char: Dnd5eCharacter) -> dict[str, Any]:
    from backend.games.dnd5e.characters.creation_choices import (
        resolved_choice_lines,
        validate_creation_choices,
    )
    from backend.games.dnd5e.characters.origin_feats import luck_points_max

    limits = spell_limits(char)
    cls = get_class(char.class_name) or {}
    entries = normalize_class_entries(char)
    slots = (
        asi_feat_slots_multiclass(char)
        if len(class_levels_dict(char)) > 1
        else (asi_feat_slots(char.class_name, char.level) if char.class_name else 0)
    )
    taken = len(char.asi_choices)
    primary = primary_class_entry(char) or {}
    return {
        "proficiency_bonus": char.proficiency_bonus(),
        "spell_limits": limits,
        "spellcasting": cls.get("spellcasting"),
        "subclass_level": cls.get("subclass_level", 3),
        "needs_subclass": any(
            int(e.get("level", 0))
            >= int((get_class(e["class_name"]) or {}).get("subclass_level", 3) or 3)
            and not e.get("subclass")
            for e in entries
        ),
        "hit_die": char.hit_die,
        "hit_dice_available": max(0, char.hit_dice_max - char.hit_dice_spent),
        "hit_dice_pool": hit_dice_pool(char),
        "asi_feat_slots": slots,
        "asi_feat_taken": taken,
        "needs_asi": slots > taken,
        "ac": char.ac,
        "classes": entries,
        "multiclass": len(class_levels_dict(char)) > 1,
        "unlocked_features": unlocked_features(char),
        "primary_class": primary.get("class_name"),
        "spell_slots_max": compute_spell_slots(char),
        "wild_shape_max": compute_wild_shape_max(char),
        "wild_shape_uses": char.wild_shape_uses,
        "creation_choices": resolved_choice_lines(char),
        "missing_creation_choices": validate_creation_choices(char),
        "luck_points_max": luck_points_max(char),
    }


def short_rest_heal(
    char: Dnd5eCharacter,
    *,
    dice_to_spend: int = 1,
) -> dict[str, Any]:
    """Spend Hit Dice during a short rest (PHB 2024)."""
    from backend.dm.audit import character_audit_slice, record_audit

    available = max(0, char.hit_dice_max - char.hit_dice_spent)
    spend = min(max(0, int(dice_to_spend)), available)
    if spend <= 0:
        return {
            "healing": 0,
            "rolls": [],
            "dice_spent": 0,
            "summary": "",
            "entity_updates": {},
        }
    before = character_audit_slice(character_to_dict(char))
    con_mod = char.ability_modifier("con")
    rolls: list[int] = []
    total = 0
    for _ in range(spend):
        roll = random.randint(1, char.hit_die)
        healed = max(1, roll + con_mod)
        rolls.append(roll)
        total += healed
        record_audit(
            {
                "event": "dice_roll",
                "source": "character_builder",
                "detail": {
                    "notation": f"1d{char.hit_die}",
                    "rolls": [roll],
                    "modifier": con_mod,
                    "total": healed,
                    "caller": "character_builder.hit_dice",
                    "inferred": False,
                },
            }
        )
    hp_before = char.hp
    new_hp = min(char.max_hp, char.hp + total)
    char.hp = new_hp
    char.hit_dice_spent = char.hit_dice_spent + spend
    after = character_audit_slice(character_to_dict(char))
    record_audit(
        {
            "event": "hp_change",
            "source": "character_builder",
            "before": before,
            "after": after,
            "detail": {
                "healing": total,
                "hp_before": hp_before,
                "hp_after": new_hp,
                "hit_dice_spent": spend,
                "inferred": False,
            },
        }
    )
    return {
        "healing": total,
        "rolls": rolls,
        "dice_spent": spend,
        "summary": (
            f"Spent {spend}d{char.hit_die} {rolls} + {con_mod:+d} CON "
            f"→ **{total}** HP restored ({char.hp - total} → {new_hp})"
        ),
        "entity_updates": {
            "hp": new_hp,
            "hit_dice_spent": char.hit_dice_spent,
        },
    }


def apply_short_rest(
    char: Dnd5eCharacter,
    *,
    dice_to_spend: int = 0,
) -> dict[str, Any]:
    """Short rest: Pact Magic recovery + optional Hit Dice healing."""
    from backend.dm.audit import character_audit_slice, record_audit

    before = character_audit_slice(character_to_dict(char))
    parts: list[str] = ["Short rest."]
    entity: dict[str, Any] = {}

    pact_line = recover_pact_slots_on_short_rest(char)
    if pact_line:
        parts.append(pact_line)
        entity["spell_slots"] = dict(char.spell_slots)

    if dice_to_spend > 0:
        heal = short_rest_heal(char, dice_to_spend=dice_to_spend)
        if heal.get("summary"):
            parts.append(heal["summary"])
        entity.update(heal.get("entity_updates") or {})

    summary = " ".join(parts)
    if summary == "Short rest.":
        summary = "Short rest (no resources spent or recovered)."
    record_audit(
        {
            "event": "rest",
            "source": "character_builder",
            "before": before,
            "after": character_audit_slice(character_to_dict(char)),
            "detail": {"kind": "short_rest", "dice_to_spend": dice_to_spend, "inferred": False},
        }
    )
    return {"summary": summary, "entity_updates": entity}


def elf_trance_rest_note(char: Dnd5eCharacter) -> str:
    """Narrative note only — elves finish a long rest in 4 hours of Trance (PHB 2024)."""
    if (char.species or "").strip().lower() == "elf":
        return " Rested in **4-hour Trance** (elf trait — same benefits as an 8-hour long rest)."
    return ""


def long_rest_recover(char: Dnd5eCharacter) -> dict[str, Any]:
    """Apply long rest recovery (HP, Hit Dice, spell slots)."""
    from backend.dm.audit import character_audit_slice, record_audit

    before = character_audit_slice(character_to_dict(char))
    char.hp = char.max_hp
    char.hit_dice_spent = 0
    char.spell_slots = compute_spell_slots(char)
    char.death_save_successes = 0
    char.death_save_failures = 0
    char.exhaustion = max(0, char.exhaustion - 1)  # PHB 2024: long rest removes 1 level
    char.concentration = ""
    char.wild_shape_uses = compute_wild_shape_max(char)
    if char.species == "human":
        char.heroic_inspiration = True
    char.clamp()
    slots = ", ".join(
        f"L{k}×{v}" for k, v in sorted(char.spell_slots.items(), key=lambda x: int(x[0]))
    )
    summary = f"Long rest: HP restored to **{char.hp}/{char.max_hp}**, all Hit Dice available"
    if slots:
        summary += f", spell slots restored ({slots})"
    ws_max = compute_wild_shape_max(char)
    if ws_max > 0:
        summary += f", Wild Shape uses restored ({ws_max}/{ws_max})"
    if char.exhaustion:
        summary += f", exhaustion now level {char.exhaustion}"
    summary += elf_trance_rest_note(char)
    record_audit(
        {
            "event": "rest",
            "source": "character_builder",
            "before": before,
            "after": character_audit_slice(character_to_dict(char)),
            "detail": {"kind": "long_rest", "inferred": False},
        }
    )
    return {
        "summary": summary,
        "entity_updates": {
            "hp": char.hp,
            "hit_dice_spent": 0,
            "spell_slots": dict(char.spell_slots),
            "heroic_inspiration": char.heroic_inspiration,
            "death_save_successes": 0,
            "death_save_failures": 0,
            "exhaustion": char.exhaustion,
            "concentration": "",
            "wild_shape_uses": char.wild_shape_uses,
        },
    }
