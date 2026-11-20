"""PHB 2024 character creation choices — resolve, validate, apply."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from backend.config import CURATED_DIR
from backend.games.dnd5e.characters.character_data import (
    equipment_data,
    get_species,
    get_weapon,
    list_weapons,
    skills_data,
    spell_list_for,
)
from backend.games.dnd5e.characters.entity import Dnd5eCharacter
from backend.games.dnd5e.characters.multiclass import normalize_class_entries
from backend.games.dnd5e.characters.origin_feats import (
    ORIGIN_FEAT_LABELS,
    apply_origin_feat_proficiencies,
    apply_proficiency_pick,
    feat_matches_when_list,
)
from backend.games.dnd5e.characters.spell_resources import normalize_spell_name

_CHOICES_PATH = CURATED_DIR / "dnd5e_creation_choices.yaml"
_MASTERY_PATH = CURATED_DIR / "dnd5e_weapon_mastery.yaml"

FIGHTING_STYLE_LABELS = {
    "archery": "Archery",
    "blindfighting": "Blind Fighting",
    "defense": "Defense",
    "dueling": "Dueling",
    "greatweaponfighting": "Great Weapon Fighting",
    "interception": "Interception",
    "protection": "Protection",
    "thrownweaponfighting": "Thrown Weapon Fighting",
    "unarmedfighting": "Unarmed Fighting",
}

STANDARD_LANGUAGES = (
    "common",
    "common sign language",
    "draconic",
    "dwarvish",
    "elvish",
    "giant",
    "gnomish",
    "goblin",
    "halfling",
    "orc",
)

# Species trait names (lowercase) mapped to creation-choice ids when the player picks a value.
TRAIT_TO_CHOICE_ID: dict[str, str] = {
    "skillful": "human_skill",
    "versatile": "versatile_origin_feat",
    "keen senses": "keen_senses_skill",
    "draconic ancestry": "draconic_ancestry",
    "giant ancestry": "giant_ancestry",
    "fiendish legacy": "fiendish_legacy",
}

# Species choices not listed as a trait line in dnd5e_species.yaml.
EXTRA_SPECIES_CHOICE_LABELS: dict[str, str] = {
    "elven_lineage": "Elven Lineage",
    "gnome_lineage": "Gnome Lineage",
    "size": "Size",
}


@lru_cache(maxsize=1)
def creation_choices_data() -> dict[str, Any]:
    if not _CHOICES_PATH.exists():
        return {}
    with _CHOICES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def weapon_mastery_data() -> dict[str, Any]:
    if not _MASTERY_PATH.exists():
        return {}
    with _MASTERY_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def mastery_property_label(prop_id: str) -> str:
    props = weapon_mastery_data().get("properties") or {}
    row = props.get(str(prop_id or "").strip().lower()) or {}
    return str(row.get("label") or prop_id or "").strip()


def weapon_mastery_label(weapon_id: str) -> str:
    w = get_weapon(weapon_id) or {}
    label = str(w.get("label") or weapon_id).strip()
    prop = str(w.get("mastery") or "").strip().lower()
    if prop:
        pl = mastery_property_label(prop)
        if pl:
            return f"{label} ({pl})"
    return label


def _resolve_options_ref(ref: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(ref, str) or not ref.startswith("$"):
        return ref if isinstance(ref, list) else []
    key = ref[1:]
    if key == "skills":
        return [
            {"id": s.get("id"), "label": s.get("label") or s.get("id")}
            for s in (skills_data().get("skills") or [])
            if isinstance(s, dict) and s.get("id")
        ]
    if key == "weapons":
        return [
            {"id": w.get("id"), "label": w.get("label") or w.get("id")}
            for w in list_weapons()
            if isinstance(w, dict) and w.get("id")
        ]
    if key == "languages":
        langs = equipment_data().get("languages") or []
        return [
            {"id": str(lang).replace(" ", "_"), "label": str(lang).replace("_", " ").title()}
            for lang in langs
        ]
    if key == "standard_languages":
        return [
            {"id": lang.replace(" ", "_"), "label": lang.replace("_", " ").title()}
            for lang in STANDARD_LANGUAGES
        ]
    if key == "origin_languages":
        return [
            {"id": lang.replace(" ", "_"), "label": lang.replace("_", " ").title()}
            for lang in STANDARD_LANGUAGES
            if lang != "common"
        ]
    if key == "extra_languages":
        skip = {"thieves' cant", "thieves cant"}
        langs = equipment_data().get("languages") or []
        return [
            {"id": str(lang).replace(" ", "_"), "label": str(lang).replace("_", " ").title()}
            for lang in langs
            if str(lang).strip().lower() not in skip
        ]
    if key == "fighting_style_feats":
        return data.get("fighting_style_feats") or []
    if key == "origin_feats":
        return data.get("origin_feats") or []
    return data.get(key) or []


def _expand_choice(raw: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    opts = raw.get("options")
    if isinstance(opts, str):
        out["options"] = _resolve_options_ref(opts, data)
    return out


def sync_feature_choice_fields(char: Dnd5eCharacter) -> None:
    """Keep legacy top-level fields and feature_choices dict in sync."""
    fc = dict(char.feature_choices or {})
    if char.human_skill and not fc.get("human_skill"):
        fc["human_skill"] = char.human_skill
    if fc.get("human_skill"):
        char.human_skill = str(fc["human_skill"]).strip().lower()
    if char.fighting_style_feat and not fc.get("fighting_style_feat"):
        fc["fighting_style_feat"] = char.fighting_style_feat
    if fc.get("fighting_style_feat"):
        char.fighting_style_feat = str(fc["fighting_style_feat"]).strip().lower()
    if char.versatile_origin_feat and not fc.get("versatile_origin_feat"):
        fc["versatile_origin_feat"] = char.versatile_origin_feat
    if fc.get("versatile_origin_feat"):
        char.versatile_origin_feat = str(fc["versatile_origin_feat"]).strip()
    if char.weapon_mastery and not fc.get("weapon_mastery"):
        fc["weapon_mastery"] = list(char.weapon_mastery)
    wm = fc.get("weapon_mastery")
    if isinstance(wm, list) and wm:
        char.weapon_mastery = [str(x).strip().lower() for x in wm if str(x).strip()]
    char.feature_choices = fc


def _choice_value(char: Dnd5eCharacter, choice_id: str) -> Any:
    sync_feature_choice_fields(char)
    fc = char.feature_choices or {}
    if choice_id == "human_skill":
        return char.human_skill or fc.get("human_skill")
    if choice_id == "fighting_style_feat":
        return char.fighting_style_feat or fc.get("fighting_style_feat")
    if choice_id == "versatile_origin_feat":
        return char.versatile_origin_feat or fc.get("versatile_origin_feat")
    if choice_id == "weapon_mastery":
        return char.weapon_mastery or fc.get("weapon_mastery")
    if choice_id == "size":
        return char.size
    return fc.get(choice_id)


def _active_feats(char: Dnd5eCharacter) -> list[str]:
    feats = []
    if char.origin_feat:
        feats.append(char.origin_feat)
    if char.versatile_origin_feat:
        feats.append(char.versatile_origin_feat)
    return feats


def _species_choices(char: Dnd5eCharacter, data: dict[str, Any]) -> list[dict[str, Any]]:
    sid = str(char.species or "").strip().lower()
    if not sid:
        return []
    rows = (data.get("species") or {}).get(sid) or []
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        expanded = _expand_choice(raw, data)
        if str(raw.get("id") or "") == "keen_senses_skill":
            expanded["options"] = [
                {"id": "insight", "label": "Insight"},
                {"id": "perception", "label": "Perception"},
                {"id": "survival", "label": "Survival"},
            ]
        lineage = str((char.feature_choices or {}).get("elven_lineage") or "").lower()
        if str(raw.get("id") or "") == "high_elf_spell_ability" and lineage not in (
            "high_elf",
            "high elf",
        ):
            continue
        out.append(expanded)
    return out


def _origin_language_choices(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("origin") or []
    return [_expand_choice(r, data) for r in rows if isinstance(r, dict)]


def _background_choices(char: Dnd5eCharacter, data: dict[str, Any]) -> list[dict[str, Any]]:
    bid = str(char.background or "").strip().lower()
    if not bid:
        return []
    rows = (data.get("backgrounds") or {}).get(bid) or []
    return [_expand_choice(r, data) for r in rows if isinstance(r, dict)]


def _subclass_matches(when_list: list[Any], char: Dnd5eCharacter, entry: dict[str, Any]) -> bool:
    if not when_list:
        return True
    from backend.games.dnd5e.characters.features import find_subclass_key

    fc = char.feature_choices or {}
    sub = str(entry.get("subclass") or char.subclass or fc.get("subclass") or "").strip()
    active = {sub.lower(), sub.lower().replace(" ", "_")}
    key = find_subclass_key(str(entry.get("class_name") or ""), sub)
    if key:
        active.add(key)
    for raw in when_list:
        token = str(raw or "").strip()
        if not token:
            continue
        low = token.lower()
        if low in active or low.replace(" ", "_") in active:
            return True
        fk = find_subclass_key(str(entry.get("class_name") or ""), token)
        if fk and fk in active:
            return True
    return False


def _class_choices_for_entry(
    char: Dnd5eCharacter,
    entry: dict[str, Any],
    data: dict[str, Any],
    *,
    target_level: int | None = None,
) -> list[dict[str, Any]]:
    cid = str(entry.get("class_name") or "").strip().lower()
    lv = int(entry.get("level") or 1)
    if not cid:
        return []
    rows = (data.get("classes") or {}).get(cid) or []
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        min_lv = int(raw.get("min_level") or 1)
        if target_level is not None:
            if min_lv != target_level:
                continue
        elif lv < min_lv:
            continue
        when_sub = raw.get("when_subclass")
        if when_sub and not _subclass_matches(
            when_sub if isinstance(when_sub, list) else [when_sub],
            char,
            entry,
        ):
            continue
        expanded = _expand_choice(raw, data)
        if str(raw.get("id") or "") == "weapon_mastery":
            from backend.games.dnd5e.characters.class_resources import mastery_weapons_for_class

            expanded["options"] = mastery_weapons_for_class(cid)
        spell_list = raw.get("spell_list")
        if spell_list:
            sl = spell_list_for(str(spell_list))
            level = int(raw.get("spell_level") or 0)
            key = "cantrips" if level == 0 else str(level)
            expanded["spell_options"] = list(sl.get(key) or sl.get("cantrips") or [])
        out.append(expanded)
    return out


def _origin_subchoices(char: Dnd5eCharacter, data: dict[str, Any]) -> list[dict[str, Any]]:
    subs = data.get("origin_feat_subchoices") or {}
    out: list[dict[str, Any]] = []
    for _key, block in subs.items():
        if not isinstance(block, dict):
            continue
        when = block.get("when_feat") or []
        if not feat_matches_when_list(when, char):
            continue
        for raw in block.get("choices") or []:
            if isinstance(raw, dict):
                expanded = _expand_choice(raw, data)
                spell_list = raw.get("spell_list")
                if spell_list:
                    sl = spell_list_for(str(spell_list))
                    level = int(raw.get("spell_level") or 0)
                    key = "cantrips" if level == 0 else str(level)
                    expanded["spell_options"] = list(sl.get(key) or sl.get("cantrips") or [])
                out.append(expanded)
    return out


def choices_for_character(
    char: Dnd5eCharacter,
    *,
    target_class: str = "",
    target_level: int | None = None,
) -> list[dict[str, Any]]:
    """All applicable creation choices for the character (or level-up target)."""
    data = creation_choices_data()
    sync_feature_choice_fields(char)
    out: list[dict[str, Any]] = []
    out.extend(_species_choices(char, data))
    out.extend(_origin_language_choices(data))
    out.extend(_background_choices(char, data))
    entries = normalize_class_entries(char)
    if target_class:
        tc = target_class.strip().lower()
        entries = [e for e in entries if e.get("class_name") == tc] or [
            {"class_name": tc, "level": int(char.level or 1) + 1}
        ]
    for entry in entries:
        out.extend(_class_choices_for_entry(char, entry, data, target_level=target_level))
    out.extend(_origin_subchoices(char, data))
    return out


def _label_for_option(choice: dict[str, Any], value: str) -> str:
    vid = str(value or "").strip().lower()
    for opt in choice.get("options") or []:
        if isinstance(opt, dict) and str(opt.get("id", "")).lower() == vid:
            return str(opt.get("label") or vid)
    if choice.get("id") == "fighting_style_feat":
        return FIGHTING_STYLE_LABELS.get(vid, vid)
    if choice.get("id") == "versatile_origin_feat":
        return ORIGIN_FEAT_LABELS.get(vid, vid)
    if choice.get("kind") == "weapons" or choice.get("id") == "weapon_mastery":
        return weapon_mastery_label(vid)
    return vid.replace("_", " ").title()


def _is_choice_complete(char: Dnd5eCharacter, choice: dict[str, Any]) -> tuple[bool, str]:
    cid = str(choice.get("id") or "")
    kind = str(choice.get("kind") or "")
    count = int(choice.get("count") or 1)
    val = _choice_value(char, cid)
    if kind in ("weapons", "skills", "invocations", "spells", "languages"):
        items = val if isinstance(val, list) else []
        if len(items) < count:
            return False, f"{choice.get('label', cid)}: pick {count}"
        return True, ""
    if kind == "spell":
        if not val:
            return False, f"{choice.get('label', cid)}: required"
        return True, ""
    if not val:
        return False, f"{choice.get('label', cid)}: required"
    return True, ""


def validate_creation_choices(char: Dnd5eCharacter) -> list[str]:
    sync_feature_choice_fields(char)
    missing: list[str] = []
    for choice in choices_for_character(char):
        ok, msg = _is_choice_complete(char, choice)
        if not ok and msg:
            missing.append(msg)
    return missing


def validate_creation_choices_at_level(
    char: Dnd5eCharacter,
    *,
    class_name: str,
    level: int,
) -> list[str]:
    sync_feature_choice_fields(char)
    missing: list[str] = []
    for choice in choices_for_character(char, target_class=class_name, target_level=level):
        ok, msg = _is_choice_complete(char, choice)
        if not ok and msg:
            missing.append(msg)
    return missing


def species_choice_ids() -> set[str]:
    """Choice ids defined under species in dnd5e_creation_choices.yaml."""
    ids: set[str] = set()
    for rows in (creation_choices_data().get("species") or {}).values():
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                ids.add(str(row["id"]))
    return ids


def _parse_trait_text(trait: str) -> tuple[str, str]:
    """Split 'Resourceful (Heroic Inspiration on Long Rest)' into name and detail."""
    text = str(trait or "").strip()
    if "(" in text and text.endswith(")"):
        idx = text.index("(")
        return text[:idx].strip(), text[idx + 1 : -1].strip()
    return text, ""


def species_trait_lines(char: Dnd5eCharacter) -> list[dict[str, str]]:
    """PHB species traits for display — automatic traits plus merged player picks."""
    sp = get_species(char.species)
    if not sp:
        return []
    picks = {row["id"]: row["value_label"] for row in resolved_choice_lines(char)}
    used_choice_ids: set[str] = set()
    lines: list[dict[str, str]] = []

    for raw in sp.get("traits") or []:
        name, default_detail = _parse_trait_text(str(raw))
        choice_id = TRAIT_TO_CHOICE_ID.get(name.lower(), "")
        pick = picks.get(choice_id) if choice_id else ""
        detail = pick or default_detail
        if choice_id and pick:
            used_choice_ids.add(choice_id)
        trait_id = choice_id or normalize_spell_name(name) or name.lower().replace(" ", "_")
        display = f"{name}: {detail}" if detail else name
        lines.append(
            {
                "id": trait_id,
                "label": name,
                "detail": detail,
                "display": display,
                "automatic": not choice_id or not pick,
            }
        )

    for choice_id, label in EXTRA_SPECIES_CHOICE_LABELS.items():
        pick = picks.get(choice_id)
        if not pick or choice_id in used_choice_ids:
            continue
        lines.append(
            {
                "id": choice_id,
                "label": label,
                "detail": pick,
                "display": f"{label}: {pick}",
                "automatic": False,
            }
        )
    return lines


def class_choice_lines(char: Dnd5eCharacter) -> list[dict[str, str]]:
    """Creation choices excluding species picks (shown under species traits)."""
    species_ids = species_choice_ids()
    return [row for row in resolved_choice_lines(char) if row["id"] not in species_ids]


def resolved_choice_lines(char: Dnd5eCharacter) -> list[dict[str, str]]:
    sync_feature_choice_fields(char)
    lines: list[dict[str, str]] = []
    for choice in choices_for_character(char):
        cid = str(choice.get("id") or "")
        val = _choice_value(char, cid)
        if not val:
            continue
        kind = str(choice.get("kind") or "")
        label = str(choice.get("label") or cid)
        if kind in ("weapons", "skills", "invocations", "spells") and isinstance(val, list):
            value_label = ", ".join(_label_for_option(choice, str(v)) for v in val)
        elif kind == "spell":
            value_label = str(val).replace("_", " ").title()
        else:
            value_label = _label_for_option(choice, str(val))
        lines.append({"id": cid, "label": label, "value": str(val), "value_label": value_label})
    return lines


def apply_creation_choices(char: Dnd5eCharacter) -> None:
    """Apply mechanical effects of recorded creation choices."""
    sync_feature_choice_fields(char)
    skills = list(char.skill_proficiencies or [])
    tools = list(char.tool_proficiencies or [])
    for choice in choices_for_character(char):
        cid = str(choice.get("id") or "")
        kind = str(choice.get("kind") or "")
        val = _choice_value(char, cid)
        if not val:
            continue
        if kind == "skill" or cid in ("human_skill", "keen_senses_skill"):
            sk = str(val).lower()
            if sk and sk not in skills:
                skills.append(sk)
        if cid == "rogue_expertise":
            picks = [str(item).strip().lower() for item in (val if isinstance(val, list) else []) if str(item).strip()]
            char.expertise = picks
            fc = dict(char.feature_choices or {})
            fc["rogue_expertise"] = picks
            char.feature_choices = fc
            continue
        if kind == "skills" or cid in (
            "skilled_proficiencies",
            "crafter_tools",
            "musician_instruments",
        ):
            for item in val if isinstance(val, list) else []:
                apply_proficiency_pick(str(item), skills, tools)
        if kind == "language" or kind == "languages" or cid in (
            "thieves_cant_language",
            "origin_languages",
        ):
            langs = list(char.languages or [])
            values = val if isinstance(val, list) else [val]
            for item in values:
                lang = str(item).lower().replace("_", " ").strip()
                if lang and lang not in langs:
                    langs.append(lang)
            char.languages = langs
        if cid == "gaming_set_kind":
            kind_label = str(val).replace("_", " ").strip()
            tools = [t for t in tools if str(t).strip().lower() not in {"gaming set", "gaming_set"}]
            if kind_label:
                tools.append(kind_label)
        if kind == "spells" or (kind == "spell" and cid.startswith("magic_initiate")):
            spell_level = int(choice.get("spell_level") or 0)
            if cid == "third_caster_spells" or (kind == "spells" and spell_level > 0):
                prepared = list(char.prepared_spells or [])
                for c in val if isinstance(val, list) else []:
                    sn = str(c)
                    if sn and sn not in prepared:
                        prepared.append(sn)
                char.prepared_spells = prepared
            else:
                cantrips = list(char.cantrips or [])
                if isinstance(val, list):
                    for c in val:
                        cn = normalize_spell_name(str(c))
                        if cn and cn not in [normalize_spell_name(x) for x in cantrips]:
                            cantrips.append(str(c))
                    char.cantrips = cantrips
                elif kind == "spell":
                    known = list(char.known_spells or [])
                    sn = str(val)
                    if sn and sn not in known:
                        known.append(sn)
                    char.known_spells = known
        if cid == "subclass" and kind == "enum":
            label = _label_for_option(choice, str(val))
            char.subclass = label
            entries = char.normalized_class_entries()
            for entry in entries:
                if entry.get("class_name") == char.class_name:
                    entry["subclass"] = label
            char.classes = entries
            char.sync_legacy_class_fields()
    char.skill_proficiencies = skills
    char.tool_proficiencies = tools
    apply_origin_feat_proficiencies(char)
    _grant_lineage_cantrips(char)
    _sync_known_languages(char)


def _norm_lang(raw: Any) -> str:
    return str(raw or "").strip().lower().replace("_", " ")


def _is_rogue(char: Dnd5eCharacter) -> bool:
    if str(char.class_name or "").lower() == "rogue":
        return True
    return any(
        str(entry.get("class_name") or "").lower() == "rogue"
        for entry in char.normalized_class_entries()
    )


SPECIES_ORIGIN_LANGUAGE = {
    "elf": "elvish",
    "dwarf": "dwarvish",
    "halfling": "halfling",
    "gnome": "gnomish",
    "orc": "orc",
    "dragonborn": "draconic",
    "goliath": "giant",
}

BACKGROUND_ORIGIN_LANGUAGE = {
    "sage": "draconic",
    "soldier": "giant",
    "criminal": "orc",
    "acolyte": "elvish",
    "guide": "giant",
    "sailor": "orc",
    "wayfarer": "goblin",
    "artisan": "dwarvish",
    "merchant": "dwarvish",
    "scribe": "draconic",
    "noble": "elvish",
    "charlatan": "elvish",
    "entertainer": "elvish",
    "farmer": "halfling",
    "hermit": "draconic",
}

_WIZARD_BOOK_EXTRAS = (
    "Burning Hands",
    "Sleep",
    "Charm Person",
    "Thunderwave",
    "Find Familiar",
    "Color Spray",
)
_MI_WIZARD_CANTRIPS = ("Minor Illusion", "Acid Splash", "Light", "Ray of Frost")


def _reserved_language_names(char: Dnd5eCharacter, fc: dict[str, Any]) -> set[str]:
    reserved = {"common", "thieves' cant", "thieves cant"}
    extra = _norm_lang(fc.get("thieves_cant_language") or "")
    if extra:
        reserved.add(extra)
    return reserved


def _has_class(char: Dnd5eCharacter, class_name: str) -> bool:
    needle = class_name.strip().lower()
    if str(char.class_name or "").lower() == needle:
        return True
    return any(
        str(entry.get("class_name") or "").lower() == needle
        for entry in char.normalized_class_entries()
    )


def _set_choice(fc: dict[str, Any], key: str, value: Any) -> bool:
    current = fc.get(key)
    if current == value:
        return False
    fc[key] = value
    return True


def _fill_origin_languages(char: Dnd5eCharacter, fc: dict[str, Any]) -> bool:
    origin_list = [_norm_lang(item) for item in (fc.get("origin_languages") or []) if _norm_lang(item)]
    if len(origin_list) >= 2:
        return False
    reserved = _reserved_language_names(char, fc)
    existing_langs = [_norm_lang(item) for item in (char.languages or []) if _norm_lang(item)]
    inferred = [lang for lang in origin_list if lang]
    for lang in existing_langs:
        if lang in reserved or lang in inferred:
            continue
        inferred.append(lang)
        if len(inferred) >= 2:
            break
    species_lang = SPECIES_ORIGIN_LANGUAGE.get(str(char.species or "").strip().lower(), "")
    background_lang = BACKGROUND_ORIGIN_LANGUAGE.get(str(char.background or "").strip().lower(), "")
    standard = [lang for lang in STANDARD_LANGUAGES if lang != "common"]
    for lang in (species_lang, background_lang, *standard):
        if not lang or lang in reserved or lang in inferred:
            continue
        inferred.append(lang)
        if len(inferred) >= 2:
            break
    inferred = inferred[:2]
    if inferred and inferred != origin_list:
        fc["origin_languages"] = inferred
        return True
    return False


def _fill_elf_defaults(char: Dnd5eCharacter, fc: dict[str, Any]) -> bool:
    if str(char.species or "").strip().lower() != "elf":
        return False
    changed = False
    lineage = str(fc.get("elven_lineage") or "").strip().lower().replace(" ", "_")
    cantrips = {normalize_spell_name(item) for item in (char.cantrips or [])}
    if not lineage:
        if "druidcraft" in cantrips:
            lineage = "wood_elf"
        elif str(char.class_name or "").lower() == "ranger":
            lineage = "wood_elf"
        else:
            lineage = "high_elf"
        changed = _set_choice(fc, "elven_lineage", lineage) or changed
    if lineage == "high_elf" and not str(fc.get("high_elf_spell_ability") or "").strip():
        from backend.games.dnd5e.characters.character_data import get_class

        cls = get_class(char.class_name) or {}
        changed = _set_choice(
            fc, "high_elf_spell_ability", str(cls.get("primary_ability") or "int").lower()
        ) or changed
    keen = str(fc.get("keen_senses_skill") or "").strip().lower()
    if not keen:
        skills = {str(item).strip().lower() for item in (char.skill_proficiencies or [])}
        pick = "perception" if "perception" in skills else "perception"
        changed = _set_choice(fc, "keen_senses_skill", pick) or changed
    return changed


def _fill_magic_initiate(char: Dnd5eCharacter, fc: dict[str, Any]) -> bool:
    feat = f"{char.origin_feat or ''} {char.versatile_origin_feat or ''}".lower()
    if "magic initiate" not in feat:
        return False
    changed = False
    list_id = "wizard"
    if "cleric" in feat:
        list_id = "cleric"
    elif "druid" in feat:
        list_id = "druid"
    cantrips = fc.get("magic_initiate_cantrips") or []
    cantrip_list = [str(item).strip() for item in cantrips if str(item).strip()]
    if len(cantrip_list) < 2:
        known = {normalize_spell_name(item) for item in (char.cantrips or [])}
        known.update(normalize_spell_name(item) for item in cantrip_list)
        extras = list(cantrip_list)
        from backend.games.dnd5e.characters.character_data import spell_list_for

        pool = list(_MI_WIZARD_CANTRIPS if list_id == "wizard" else []) + list(
            spell_list_for(list_id).get("cantrips") or []
        )
        for name in pool:
            key = normalize_spell_name(name)
            if not key or key in known:
                continue
            extras.append(name)
            known.add(key)
            if len(extras) >= 2:
                break
        if extras:
            changed = _set_choice(fc, "magic_initiate_cantrips", extras[:2]) or changed
    if not str(fc.get("magic_initiate_level1") or "").strip():
        prepared = [str(item).strip() for item in (char.prepared_spells or []) if str(item).strip()]
        pick = ""
        for name in prepared:
            if normalize_spell_name(name) == "shield":
                pick = name
                break
        if not pick:
            for name in prepared:
                if normalize_spell_name(name) != "magearmor":
                    pick = name
                    break
        if not pick and prepared:
            pick = prepared[0]
        if not pick:
            pick = "Shield" if list_id == "wizard" else ""
        if pick:
            changed = _set_choice(fc, "magic_initiate_level1", pick) or changed
    if not str(fc.get("magic_initiate_ability") or "").strip():
        ability = "int" if list_id == "wizard" else "wis"
        changed = _set_choice(fc, "magic_initiate_ability", ability) or changed
    return changed


def _fill_wizard_spellbook(char: Dnd5eCharacter) -> bool:
    if not _has_class(char, "wizard"):
        return False
    from backend.games.dnd5e.characters.character_data import spell_list_for

    level = max(1, int(char.level or 1))
    need = 6 + 2 * (level - 1)
    book = list(char.spellbook or [])
    seen = {normalize_spell_name(item) for item in book}
    changed = False
    for name in char.prepared_spells or []:
        key = normalize_spell_name(str(name))
        if key and key not in seen:
            book.append(str(name).strip())
            seen.add(key)
            changed = True
    if len(book) < need:
        pool = list(_WIZARD_BOOK_EXTRAS) + list(spell_list_for("wizard").get("1") or [])
        for name in pool:
            key = normalize_spell_name(name)
            if not key or key in seen:
                continue
            book.append(name)
            seen.add(key)
            changed = True
            if len(book) >= need:
                break
    if changed:
        char.spellbook = book
    return changed


def migrate_legacy_sheet(char: Dnd5eCharacter) -> bool:
    """Backfill 2024 origin picks, High Elf ability, and wizard spellbook without wiping picks."""
    changed = False
    fc = dict(char.feature_choices or {})
    changed = _fill_origin_languages(char, fc) or changed
    changed = _fill_elf_defaults(char, fc) or changed
    changed = _fill_magic_initiate(char, fc) or changed
    if not str(fc.get("gaming_set_kind") or "").strip() and str(char.background or "").lower() == "soldier":
        changed = _set_choice(fc, "gaming_set_kind", "dice_set") or changed
    changed = _fill_wizard_spellbook(char) or changed
    if changed:
        char.feature_choices = fc
    return changed


def _grant_lineage_cantrips(char: Dnd5eCharacter) -> None:
    fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
    lineage = str(fc.get("elven_lineage") or "").strip().lower().replace(" ", "_")
    if str(char.species or "").strip().lower() != "elf" or lineage != "high_elf":
        return
    cantrips = list(char.cantrips or [])
    names = {normalize_spell_name(item) for item in cantrips}
    if "prestidigitation" not in names:
        cantrips.append("Prestidigitation")
        char.cantrips = cantrips


def _sync_known_languages(char: Dnd5eCharacter) -> None:
    fc = char.feature_choices if isinstance(char.feature_choices, dict) else {}
    langs: list[str] = []

    def add(raw: Any) -> None:
        lang = _norm_lang(raw)
        if lang and lang not in langs:
            langs.append(lang)

    add("common")
    for item in fc.get("origin_languages") or []:
        add(item)
    if _is_rogue(char):
        add("thieves' cant")
        extra = str(fc.get("thieves_cant_language") or "").strip()
        if extra.lower().replace("_", " ") not in {"thieves' cant", "thieves cant"}:
            add(extra)
    # Keep languages the player already recorded so rebuild does not wipe them.
    for item in char.languages or []:
        add(item)
    char.languages = langs


def fighting_style_feat_display(feat_id: str) -> str:
    fid = str(feat_id or "").strip().lower()
    return FIGHTING_STYLE_LABELS.get(fid, fid.replace("_", " ").title())


def collect_derived_feats(char: Dnd5eCharacter) -> list[str]:
    """Fighting style and similar feats from creation choices (not ASI feats)."""
    sync_feature_choice_fields(char)
    names: list[str] = []
    if char.fighting_style_feat:
        label = fighting_style_feat_display(char.fighting_style_feat)
        if label and label not in names:
            names.append(label)
    return names


def creation_choices_catalog(*, include_faerun: bool = False) -> dict[str, Any]:
    data = creation_choices_data()
    keys = (
        "fighting_style_feats",
        "origin_feats",
        "draconic_ancestries",
        "elven_lineages",
        "gnome_lineages",
        "giant_ancestries",
        "fiendish_legacies",
        "favored_enemies",
        "divine_orders",
        "primal_orders",
        "eldritch_invocations",
    )
    out: dict[str, Any] = {
        "species": data.get("species") or {},
        "classes": data.get("classes") or {},
        "origin": data.get("origin") or [],
        "backgrounds": data.get("backgrounds") or {},
        "origin_feat_subchoices": data.get("origin_feat_subchoices") or {},
        "include_faerun": include_faerun,
    }
    for key in keys:
        out[key] = data.get(key) or []
    return out
