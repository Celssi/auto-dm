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
    return [_expand_choice(r, data) for r in rows if isinstance(r, dict)]


def _class_choices_for_entry(
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
        out.append(_expand_choice(raw, data))
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
    entries = normalize_class_entries(char)
    if target_class:
        tc = target_class.strip().lower()
        entries = [e for e in entries if e.get("class_name") == tc] or [
            {"class_name": tc, "level": int(char.level or 1) + 1}
        ]
    for entry in entries:
        out.extend(_class_choices_for_entry(entry, data, target_level=target_level))
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
    if kind in ("weapons", "skills", "invocations", "spells"):
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
        if kind == "skills" or cid in (
            "rogue_expertise",
            "skilled_proficiencies",
            "crafter_tools",
            "musician_instruments",
        ):
            for item in val if isinstance(val, list) else []:
                apply_proficiency_pick(str(item), skills, tools)
        if kind == "language" or cid == "thieves_cant_language":
            lang = str(val).lower().replace("_", " ")
            langs = list(char.languages or [])
            if lang and lang not in langs:
                langs.append(lang)
            char.languages = langs
        if kind == "spells" or (kind == "spell" and cid.startswith("magic_initiate")):
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
    char.skill_proficiencies = skills
    char.tool_proficiencies = tools
    apply_origin_feat_proficiencies(char)


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
        "origin_feat_subchoices": data.get("origin_feat_subchoices") or {},
        "include_faerun": include_faerun,
    }
    for key in keys:
        out[key] = data.get(key) or []
    return out
