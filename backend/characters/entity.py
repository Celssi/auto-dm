"""D&D 5e character entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")

DEFAULT_ABILITY_SCORES: dict[str, int] = {k: 10 for k in ABILITY_KEYS}

CURRENCY_KEYS = ("cp", "sp", "ep", "gp", "pp")

CAMPAIGN_SETTING_OPTIONS: list[dict[str, str]] = [
    {"id": "freeform", "label": "Freeform / homebrew"},
    {"id": "faerun", "label": "Faerûn (Forgotten Realms)"},
]


def campaign_setting_line(char: Dnd5eCharacter) -> str:
    setting = (char.campaign_setting or "freeform").strip().lower()
    notes = (char.campaign_notes or "").strip()
    if setting == "faerun":
        return "The adventure is set in Faerûn (Forgotten Realms)."
    if notes:
        return f"The adventure uses a custom setting: {notes}"
    return "The adventure uses a freeform homebrew setting of the player's choosing."


@dataclass
class Dnd5eCharacter:
    id: str = ""
    name: str = ""
    species: str = ""
    size: str = "medium"
    class_name: str = ""
    subclass: str = ""
    background: str = ""
    alignment: str = ""
    level: int = 1
    xp: int = 0
    hp: int = 0
    max_hp: int = 0
    ac: int = 10
    speed: int = 30
    hit_die: int = 8
    hit_dice_max: int = 1
    hit_dice_spent: int = 0
    ability_scores: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_ABILITY_SCORES))
    base_ability_scores: dict[str, int] = field(default_factory=dict)
    ability_scores_set: bool = False
    background_asi_plus2: str = ""
    background_asi_plus1: str = ""
    background_asi_all_three: bool = False
    background_asi_mode: str = "auto"  # auto | manual
    skill_proficiencies: list[str] = field(default_factory=list)
    save_proficiencies: list[str] = field(default_factory=list)
    tool_proficiencies: list[str] = field(default_factory=list)
    class_skill_choices: list[str] = field(default_factory=list)
    human_skill: str = ""
    origin_feat: str = ""
    languages: list[str] = field(default_factory=lambda: ["common"])
    cantrips: list[str] = field(default_factory=list)
    prepared_spells: list[str] = field(default_factory=list)
    known_spells: list[str] = field(default_factory=list)
    spell_slots: dict[str, int] = field(default_factory=dict)
    heroic_inspiration: bool = False
    armor: str = "none"
    shield: bool = False
    ac_manual: bool = False
    weapons: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    currency: dict[str, int] = field(default_factory=dict)
    equipment_notes: str = ""
    asi_choices: list[dict[str, Any]] = field(default_factory=list)
    feats: list[str] = field(default_factory=list)
    death_save_successes: int = 0
    death_save_failures: int = 0
    exhaustion: int = 0
    conditions: list[str] = field(default_factory=list)
    concentration: str = ""
    wild_shape_uses: int = 0
    campaign_setting: str = "freeform"
    campaign_notes: str = ""
    last_roll_summary: str = ""
    classes: list[dict[str, Any]] = field(default_factory=list)

    def normalized_class_entries(self) -> list[dict[str, Any]]:
        from backend.characters.multiclass import normalize_class_entries

        return normalize_class_entries(self)

    def sync_legacy_class_fields(self) -> None:
        from backend.characters.multiclass import sync_legacy_class_fields

        sync_legacy_class_fields(self)

    def clamp(self) -> None:
        self.name = str(self.name or "").strip()
        self.species = str(self.species or "").strip()
        self.size = str(self.size or "medium").strip().lower()
        self.class_name = str(self.class_name or "").strip()
        self.subclass = str(self.subclass or "").strip()
        self.background = str(self.background or "").strip()
        self.alignment = str(self.alignment or "").strip()
        self.level = max(1, min(20, int(self.level or 1)))
        self.xp = max(0, int(self.xp or 0))
        self.hp = max(0, int(self.hp or 0))
        self.max_hp = max(0, int(self.max_hp or 0))
        if self.max_hp and self.hp > self.max_hp:
            self.hp = self.max_hp
        self.ac = max(1, min(30, int(self.ac or 10)))
        self.speed = max(5, min(120, int(self.speed or 30)))
        self.hit_die = max(4, min(12, int(self.hit_die or 8)))
        self.hit_dice_max = max(0, min(20, int(self.hit_dice_max or self.level)))
        self.hit_dice_spent = max(0, min(self.hit_dice_max, int(self.hit_dice_spent or 0)))
        scores = self.ability_scores if isinstance(self.ability_scores, dict) else {}
        self.ability_scores = {
            k: max(1, min(30, int(scores.get(k, 10) or 10))) for k in ABILITY_KEYS
        }
        base = self.base_ability_scores if isinstance(self.base_ability_scores, dict) else {}
        self.base_ability_scores = {
            k: max(1, min(30, int(base[k] or 10))) for k in ABILITY_KEYS if k in base
        }
        slots = self.spell_slots if isinstance(self.spell_slots, dict) else {}
        self.spell_slots = {
            str(k): max(0, min(20, int(v or 0))) for k, v in slots.items() if str(k).isdigit()
        }
        self.skill_proficiencies = _clean_list(self.skill_proficiencies, 18)
        self.save_proficiencies = _clean_list(self.save_proficiencies, 6)
        self.tool_proficiencies = _clean_list(self.tool_proficiencies, 12)
        self.class_skill_choices = _clean_list(self.class_skill_choices, 4)
        self.languages = _clean_list(self.languages, 12) or ["common"]
        self.cantrips = _clean_list(self.cantrips, 12)
        self.prepared_spells = _clean_list(self.prepared_spells, 40)
        self.known_spells = _clean_list(self.known_spells, 40)
        self.human_skill = str(self.human_skill or "").strip().lower()
        self.origin_feat = str(self.origin_feat or "").strip()
        self.armor = str(self.armor or "none").strip().lower() or "none"
        self.shield = bool(self.shield)
        self.ac_manual = bool(self.ac_manual)
        self.weapons = _clean_weapons(self.weapons)
        self.inventory = _clean_list(self.inventory, 60)
        self.currency = {
            k: max(0, int(v or 0))
            for k, v in (self.currency or {}).items()
            if k in CURRENCY_KEYS and str(v).lstrip("-").isdigit()
        }
        self.asi_choices = _clean_asi_choices(self.asi_choices)
        self.feats = _clean_list(self.feats, 12)
        self.death_save_successes = max(0, min(3, int(self.death_save_successes or 0)))
        self.death_save_failures = max(0, min(3, int(self.death_save_failures or 0)))
        self.exhaustion = max(0, min(6, int(self.exhaustion or 0)))
        self.conditions = _clean_list(self.conditions, 12)
        self.concentration = str(self.concentration or "").strip()[:80]
        self.wild_shape_uses = max(0, min(10, int(self.wild_shape_uses or 0)))
        self.equipment_notes = str(self.equipment_notes or "").strip()
        setting = str(self.campaign_setting or "freeform").strip().lower()
        self.campaign_setting = setting if setting in {"freeform", "faerun"} else "freeform"
        self.campaign_notes = str(self.campaign_notes or "").strip()[:500]
        self.last_roll_summary = str(self.last_roll_summary or "").strip()
        self._normalize_classes_field()
        self.sync_legacy_class_fields()

    def _normalize_classes_field(self) -> None:
        if not isinstance(self.classes, list):
            self.classes = []
            return
        cleaned: list[dict[str, Any]] = []
        for item in self.classes:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("class_name") or "").strip().lower()
            lv = max(0, min(20, int(item.get("level", 0) or 0)))
            if not cid or lv <= 0:
                continue
            cleaned.append(
                {
                    "class_name": cid,
                    "level": lv,
                    "subclass": str(item.get("subclass") or "").strip(),
                    "class_skill_choices": _clean_list(item.get("class_skill_choices"), 4),
                }
            )
        self.classes = cleaned

    def ability_modifier(self, ability: str) -> int:
        score = int(self.ability_scores.get(ability.lower(), 10) or 10)
        return (score - 10) // 2

    def proficiency_bonus(self) -> int:
        return 2 + (self.level - 1) // 4

    def header_fields(self) -> dict[str, Any]:
        return {
            "species": self.species,
            "class_name": self.class_name,
            "subclass": self.subclass,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "proficiency_bonus": self.proficiency_bonus(),
        }


def _clean_list(raw: Any, limit: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        s = str(item or "").strip().lower()
        if s and s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _clean_weapons(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        if not name:
            continue
        ability = str(item.get("ability", "str") or "str").strip().lower()
        if ability not in ABILITY_KEYS:
            ability = "str"
        out.append(
            {
                "name": name[:60],
                "damage": str(item.get("damage", "") or "").strip()[:20],
                "damage_type": str(item.get("damage_type", "") or "").strip().lower()[:20],
                "ability": ability,
                "proficient": bool(item.get("proficient", True)),
            }
        )
        if len(out) >= 20:
            break
    return out


def _clean_asi_choices(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", "asi") or "asi").strip().lower()
        level = max(1, min(20, int(item.get("level", 0) or 0))) if item.get("level") else 0
        if kind == "feat":
            name = str(item.get("feat", "") or "").strip()
            if not name:
                continue
            out.append({"type": "feat", "feat": name[:60], "level": level})
        else:
            plus_raw = item.get("plus") if isinstance(item.get("plus"), dict) else {}
            plus = {
                k: max(0, min(2, int(v or 0))) for k, v in plus_raw.items() if k in ABILITY_KEYS
            }
            plus = {k: v for k, v in plus.items() if v > 0}
            if not plus:
                continue
            out.append({"type": "asi", "plus": plus, "level": level})
        if len(out) >= 10:
            break
    return out


def default_character() -> Dnd5eCharacter:
    return Dnd5eCharacter(hp=10, max_hp=10)


def character_from_dict(data: dict[str, Any] | None) -> Dnd5eCharacter:
    if not data:
        return default_character()
    scores = data.get("ability_scores") or {}
    slots = data.get("spell_slots") or {}
    char = Dnd5eCharacter(
        id=str(data.get("id", "") or ""),
        name=str(data.get("name", "") or ""),
        species=str(data.get("species", "") or ""),
        size=str(data.get("size", "medium") or "medium"),
        class_name=str(data.get("class_name", "") or ""),
        subclass=str(data.get("subclass", "") or ""),
        background=str(data.get("background", "") or ""),
        alignment=str(data.get("alignment", "") or ""),
        level=int(data.get("level", 1) or 1),
        xp=int(data.get("xp", 0) or 0),
        hp=int(data.get("hp", 0) or 0),
        max_hp=int(data.get("max_hp", 0) or 0),
        ac=int(data.get("ac", 10) or 10),
        speed=int(data.get("speed", 30) or 30),
        hit_die=int(data.get("hit_die", 8) or 8),
        hit_dice_max=int(data.get("hit_dice_max", data.get("level", 1)) or 1),
        hit_dice_spent=int(data.get("hit_dice_spent", 0) or 0),
        ability_scores=dict(scores) if isinstance(scores, dict) else dict(DEFAULT_ABILITY_SCORES),
        base_ability_scores=dict(data.get("base_ability_scores") or {})
        if isinstance(data.get("base_ability_scores"), dict)
        else {},
        ability_scores_set=bool(data.get("ability_scores_set", False)),
        background_asi_plus2=str(data.get("background_asi_plus2", "") or ""),
        background_asi_plus1=str(data.get("background_asi_plus1", "") or ""),
        background_asi_all_three=bool(data.get("background_asi_all_three", False)),
        background_asi_mode=str(data.get("background_asi_mode", "auto") or "auto"),
        skill_proficiencies=_clean_list(data.get("skill_proficiencies"), 18),
        save_proficiencies=_clean_list(data.get("save_proficiencies"), 6),
        tool_proficiencies=_clean_list(data.get("tool_proficiencies"), 12),
        class_skill_choices=_clean_list(data.get("class_skill_choices"), 4),
        human_skill=str(data.get("human_skill", "") or ""),
        origin_feat=str(data.get("origin_feat", "") or ""),
        languages=_clean_list(data.get("languages"), 12) or ["common"],
        cantrips=_clean_list(data.get("cantrips"), 12),
        prepared_spells=_clean_list(data.get("prepared_spells"), 40),
        known_spells=_clean_list(data.get("known_spells"), 40),
        spell_slots=dict(slots) if isinstance(slots, dict) else {},
        heroic_inspiration=bool(data.get("heroic_inspiration", False)),
        armor=str(data.get("armor", "none") or "none"),
        shield=bool(data.get("shield", False)),
        ac_manual=bool(data.get("ac_manual", False)),
        weapons=list(data.get("weapons") or []),
        inventory=_clean_list(data.get("inventory"), 60),
        currency=dict(data.get("currency") or {}) if isinstance(data.get("currency"), dict) else {},
        equipment_notes=str(data.get("equipment_notes", "") or ""),
        asi_choices=list(data.get("asi_choices") or []),
        feats=_clean_list(data.get("feats"), 12),
        death_save_successes=int(data.get("death_save_successes", 0) or 0),
        death_save_failures=int(data.get("death_save_failures", 0) or 0),
        exhaustion=int(data.get("exhaustion", 0) or 0),
        conditions=_clean_list(data.get("conditions"), 12),
        concentration=str(data.get("concentration", "") or ""),
        wild_shape_uses=int(data.get("wild_shape_uses", 0) or 0),
        campaign_setting=str(data.get("campaign_setting", "freeform") or "freeform"),
        campaign_notes=str(data.get("campaign_notes", "") or ""),
        last_roll_summary=str(data.get("last_roll_summary") or ""),
        classes=list(data.get("classes") or []),
    )
    char.clamp()
    return char


def character_to_dict(char: Dnd5eCharacter) -> dict[str, Any]:
    char.clamp()
    return {
        "id": char.id,
        "name": char.name,
        "species": char.species,
        "size": char.size,
        "class_name": char.class_name,
        "subclass": char.subclass,
        "background": char.background,
        "alignment": char.alignment,
        "level": char.level,
        "xp": char.xp,
        "hp": char.hp,
        "max_hp": char.max_hp,
        "ac": char.ac,
        "speed": char.speed,
        "hit_die": char.hit_die,
        "hit_dice_max": char.hit_dice_max,
        "hit_dice_spent": char.hit_dice_spent,
        "ability_scores": dict(char.ability_scores),
        "base_ability_scores": dict(char.base_ability_scores),
        "ability_scores_set": char.ability_scores_set,
        "background_asi_plus2": char.background_asi_plus2,
        "background_asi_plus1": char.background_asi_plus1,
        "background_asi_all_three": char.background_asi_all_three,
        "background_asi_mode": char.background_asi_mode,
        "skill_proficiencies": list(char.skill_proficiencies),
        "save_proficiencies": list(char.save_proficiencies),
        "tool_proficiencies": list(char.tool_proficiencies),
        "class_skill_choices": list(char.class_skill_choices),
        "human_skill": char.human_skill,
        "origin_feat": char.origin_feat,
        "languages": list(char.languages),
        "cantrips": list(char.cantrips),
        "prepared_spells": list(char.prepared_spells),
        "known_spells": list(char.known_spells),
        "spell_slots": dict(char.spell_slots),
        "heroic_inspiration": char.heroic_inspiration,
        "armor": char.armor,
        "shield": char.shield,
        "ac_manual": char.ac_manual,
        "weapons": list(char.weapons),
        "inventory": list(char.inventory),
        "currency": dict(char.currency),
        "equipment_notes": char.equipment_notes,
        "asi_choices": list(char.asi_choices),
        "feats": list(char.feats),
        "death_save_successes": char.death_save_successes,
        "death_save_failures": char.death_save_failures,
        "exhaustion": char.exhaustion,
        "conditions": list(char.conditions),
        "concentration": char.concentration,
        "wild_shape_uses": char.wild_shape_uses,
        "campaign_setting": char.campaign_setting,
        "campaign_notes": char.campaign_notes,
        "last_roll_summary": char.last_roll_summary,
        "classes": list(char.classes),
    }


def format_summary(char: Dnd5eCharacter) -> str:
    parts = [char.name or "Character"]
    if char.species:
        parts.append(char.species.replace("_", " ").title())
    if char.class_name:
        label = char.class_name.replace("_", " ").title()
        if char.subclass:
            label = f"{label} ({char.subclass})"
        entries = char.normalized_class_entries()
        if len(entries) > 1:
            parts.append(
                " / ".join(
                    f"{e['class_name'].title()} {e['level']}"
                    + (f" ({e['subclass']})" if e.get("subclass") else "")
                    for e in entries
                )
            )
        else:
            parts.append(f"{label} {char.level}")
    if char.max_hp:
        parts.append(f"HP {char.hp}/{char.max_hp}")
    if char.ac:
        parts.append(f"AC {char.ac}")
    return " · ".join(parts)


def format_for_prompt(
    char: Dnd5eCharacter | None,
    *,
    story_mode: str = "player",
    card_source: str = "virtual",
) -> str:
    if not char:
        return ""
    scores = ", ".join(f"{k.upper()} {char.ability_scores.get(k, 10)}" for k in ABILITY_KEYS)
    skills = ", ".join(char.skill_proficiencies) or "(none)"
    cantrips = ", ".join(char.cantrips) or "(none)"
    spells = ", ".join(char.prepared_spells or char.known_spells) or "(none)"
    feats = (
        ", ".join([char.origin_feat] + list(char.feats))
        if (char.origin_feat or char.feats)
        else "(none)"
    )
    armor_line = (
        char.armor.replace("_", " ") if char.armor and char.armor != "none" else "unarmored"
    )
    if char.shield:
        armor_line += " + shield"
    weapons = (
        "; ".join(
            f"{w.get('name')} ({w.get('damage', '')} {w.get('damage_type', '')}, {str(w.get('ability', 'str')).upper()})".strip()
            for w in char.weapons
        )
        or "(none)"
    )
    coins = ", ".join(f"{char.currency[k]}{k}" for k in CURRENCY_KEYS if char.currency.get(k))
    from backend.characters.character_builder import compute_spell_slots
    from backend.characters.features import features_summary_lines
    from backend.characters.spell_resources import compute_wild_shape_max

    max_slots = compute_spell_slots(char)
    slot_parts: list[str] = []
    all_levels = sorted(
        {int(k) for k in max_slots} | {int(k) for k in char.spell_slots if str(k).isdigit()}
    )
    for lvl in all_levels:
        rem = int(char.spell_slots.get(str(lvl), 0) or 0)
        mx = int(max_slots.get(str(lvl), 0) or 0)
        if mx > 0:
            slot_parts.append(f"L{lvl}:{rem}/{mx}")
    slots = ", ".join(slot_parts) if slot_parts else "(none)"
    ws_max = compute_wild_shape_max(char)

    mc_parts = []
    for e in char.normalized_class_entries():
        part = f"{e['class_name']} {e['level']}"
        if e.get("subclass"):
            part += f" ({e['subclass']})"
        mc_parts.append(part)
    mc_line = ", ".join(mc_parts) if mc_parts else "(single class)"
    feature_lines = features_summary_lines(char)
    lines = [
        "Current D&D 5e character:",
        f"- Name: {char.name or 'unnamed'}",
        f"- Species: {char.species or '(not set)'} ({char.size})",
        f"- Class: {char.class_name or '(not set)'} / {char.subclass or '(no subclass)'} (total level {char.level})",
        f"- Multiclass: {mc_line}",
        f"- Background: {char.background or '(not set)'}",
        f"- Alignment: {char.alignment or '(not set)'}",
        f"- HP: {char.hp}/{char.max_hp} (Hit Die d{char.hit_die}, {char.hit_dice_max - char.hit_dice_spent} left)",
        f"- AC: {char.ac} ({armor_line}) | Speed: {char.speed} ft.",
        f"- Ability scores: {scores}",
        f"- Skill proficiencies: {skills}",
        f"- Save proficiencies: {', '.join(char.save_proficiencies) or '(none)'}",
        f"- Languages: {', '.join(char.languages) or '(none)'}",
        f"- Feats: {feats}",
        f"- Class features: {'; '.join(feature_lines) or '(none)'}",
        f"- Weapons: {weapons}",
        f"- Cantrips: {cantrips}",
        f"- Spells: {spells}",
        f"- Spell slots: {slots or '(none)'}",
        f"- Proficiency bonus: +{char.proficiency_bonus()}",
        f"- Heroic Inspiration: {'yes' if char.heroic_inspiration else 'no'}",
        f"- Exhaustion: level {char.exhaustion}"
        + (f" (−{char.exhaustion} to d20 tests)" if char.exhaustion else ""),
        f"- Conditions: {', '.join(char.conditions) or '(none)'}",
        f"- Concentration: {char.concentration or '(none)'}",
    ]
    if ws_max > 0:
        lines.append(f"- Wild Shape uses: {char.wild_shape_uses}/{ws_max}")
    lines.extend(
        [
            f"- Death saves: {char.death_save_successes} success / {char.death_save_failures} failure"
            if char.max_hp and char.hp == 0
            else "- Death saves: (not dying)",
            f"- Currency: {coins or '(none)'}",
            f"- Campaign: {char.campaign_setting or 'freeform'}"
            + (f" — {char.campaign_notes}" if char.campaign_notes else ""),
            f"- Story mode: {story_mode}",
            f"- Deck: {card_source}",
        ]
    )
    return "\n".join(lines)
