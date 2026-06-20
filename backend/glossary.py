"""Static + RAG glossary for UI tooltips (spells, gear, features)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from backend.characters.character_data import (
    equipment_data,
    list_backgrounds,
    list_classes,
    list_species,
    skills_data,
    spells_data,
)
from backend.characters.glossary_data import glossary_db_index
from backend.characters.spell_resources import build_spell_index, normalize_spell_name

_LEVEL_NAMES = {
    0: "Cantrip",
    1: "1st-level",
    2: "2nd-level",
    3: "3rd-level",
    4: "4th-level",
    5: "5th-level",
    6: "6th-level",
    7: "7th-level",
    8: "8th-level",
    9: "9th-level",
}


def _spell_summary(name: str, level: int) -> str | None:
    """Fallback only when glossary DB has no entry."""
    return None


def _weapon_summary(w: dict[str, Any]) -> str:
    props = w.get("properties") or []
    prop_text = f" Properties: {', '.join(str(p) for p in props)}." if props else ""
    return (
        f"{w.get('label', 'Weapon')} — {w.get('damage', '?')} {w.get('damage_type', '')} damage "
        f"({w.get('category', 'weapon')}).{prop_text}"
    )


def _join_limited(items: list[Any], *, max_items: int = 5, sep: str = ", ") -> str:
    if not items:
        return ""
    shown = [str(x) for x in items[:max_items]]
    text = sep.join(shown)
    if len(items) > max_items:
        text += f" (+{len(items) - max_items} more)"
    return text


def _class_summary(c: dict[str, Any]) -> str:
    hd = c.get("hit_die")
    pa = str(c.get("primary_ability") or "").upper()
    saves = ", ".join(str(s).upper() for s in (c.get("saving_throws") or []))
    armor = _join_limited(c.get("armor_training") or [])
    sc = int(c.get("skill_choices") or 0)
    spell = c.get("spellcasting")
    parts = [f"2024 PHB class. Hit Die d{hd}."]
    if pa:
        parts.append(f"Primary ability {pa}.")
    if saves:
        parts.append(f"Saving throws: {saves}.")
    if spell:
        parts.append(f"{str(spell).title()} spellcaster.")
    else:
        parts.append("Martial — no spellcasting.")
    if armor:
        parts.append(f"Armor: {armor}.")
    if sc:
        parts.append(f"Pick {sc} skill(s) from the class list.")
    sub_lvl = c.get("subclass_level")
    subs = c.get("subclasses") or []
    if sub_lvl and subs:
        parts.append(f"Subclass at level {sub_lvl}.")
    return " ".join(parts)


def _species_summary(s: dict[str, Any]) -> str:
    speed = s.get("speed", 30)
    sizes = _join_limited([str(x).title() for x in (s.get("size_options") or ["medium"])])
    traits = _join_limited(s.get("traits") or [], max_items=6)
    parts = [f"Playable species. Speed {speed} ft. Size: {sizes}."]
    if traits:
        parts.append(f"Traits: {traits}.")
    return " ".join(parts)


def _background_summary(b: dict[str, Any]) -> str:
    abs_scores = ", ".join(str(a).upper() for a in (b.get("ability_scores") or []))
    feat = str(b.get("feat") or "")
    skills = ", ".join(str(sk).replace("_", " ").title() for sk in (b.get("skills") or []))
    tool = str(b.get("tool") or "")
    if b.get("source") == "faerun":
        parts = ["Heroes of Faerûn background."]
    else:
        parts = ["2024 PHB background."]
    if abs_scores:
        parts.append(f"Ability boosts: {abs_scores}.")
    if feat:
        parts.append(f"Origin feat: {feat}.")
    if skills:
        parts.append(f"Skills: {skills}.")
    if tool:
        parts.append(f"Tool: {tool}.")
    return " ".join(parts)


def _armor_summary(a: dict[str, Any]) -> str:
    cat = a.get("category", "armor")
    ac = a.get("base_ac", 10)
    extra = ""
    if a.get("dex_cap") is not None:
        extra = f" + Dex (max {a['dex_cap']})"
    elif a.get("add_dex"):
        extra = " + Dex"
    if a.get("strength"):
        extra += f". Requires Str {a['strength']}"
    return f"{a.get('label', 'Armor')} — {cat.title()} armor. Base AC {ac}{extra}."


@lru_cache(maxsize=1)
def build_glossary_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = dict(glossary_db_index())

    spell_names: dict[str, str] = {}
    for _class_id, by_level in (spells_data().get("spell_lists") or {}).items():
        if not isinstance(by_level, dict):
            continue
        for level_key, names in by_level.items():
            if not isinstance(names, list):
                continue
            for name in names:
                spell_names[normalize_spell_name(str(name))] = str(name)

    for key, level in build_spell_index().items():
        if key in index and index[key].get("summary"):
            if index[key].get("level") is None:
                index[key]["level"] = level
            continue
        display = spell_names.get(key, key)
        summary = _spell_summary(display, level)
        index[key] = {
            "kind": "spell",
            "title": display,
            "summary": summary,
            "level": level,
        }
        if not summary:
            index[key]["summary"] = None

    for w in equipment_data().get("weapons") or []:
        if not isinstance(w, dict):
            continue
        label = str(w.get("label") or w.get("id") or "")
        key = normalize_spell_name(label)
        if key:
            index[key] = {"kind": "weapon", "title": label, "summary": _weapon_summary(w)}

    for a in equipment_data().get("armor") or []:
        if not isinstance(a, dict) or a.get("id") == "none":
            continue
        label = str(a.get("label") or a.get("id") or "")
        key = normalize_spell_name(label)
        if key:
            index[key] = {"kind": "armor", "title": label, "summary": _armor_summary(a)}

    for lang in equipment_data().get("languages") or []:
        label = str(lang).replace("_", " ").title()
        key = normalize_spell_name(str(lang))
        index[key] = {
            "kind": "language",
            "title": label,
            "summary": f"{label} — A language your character may speak, read, or write.",
        }

    for sk in skills_data().get("skills") or []:
        if not isinstance(sk, dict):
            continue
        label = str(sk.get("label") or sk.get("id") or "")
        key = normalize_spell_name(str(sk.get("id") or label))
        if key in index and index[key].get("summary"):
            continue
        ab = str(sk.get("ability") or "").upper()
        index[key] = {
            "kind": "skill",
            "title": label,
            "summary": f"{label} ({ab}) — D&D skill check using your {ab} modifier.",
        }

    # Common gear phrases (partial coverage for starting equipment)
    common_items = {
        "explorerspack": (
            "Explorer's Pack",
            "Backpack, bedroll, mess kit, tinderbox, torches, rations, waterskin, and rope.",
        ),
        "explorers pack": (
            "Explorer's Pack",
            "Backpack, bedroll, mess kit, tinderbox, torches, rations, waterskin, and rope.",
        ),
        "potionofhealing": (
            "Potion of Healing",
            "Uncommon potion. Drink as a Bonus Action to regain 2d4 + 2 HP.",
        ),
        "goodberry": (
            "Goodberry",
            "Level 1 spell. Creates berries that restore 1 HP each (up to 10 per casting).",
        ),
        "druidicfocus": (
            "Druidic Focus",
            "Spellcasting focus for druid spells "
            "(may replace material components "
            "without a listed cost).",
        ),
        "holy symbol": ("Holy Symbol", "Spellcasting focus for cleric/paladin spells."),
        "spellbook": (
            "Spellbook",
            "Wizard spell repository. Required to prepare wizard spells from your book.",
        ),
        "thieves tools": ("Thieves' Tools", "Tool used for picking locks and disarming traps."),
        "herbalism kit": (
            "Herbalism Kit",
            "Tools for identifying and applying herbs; "
            "used for crafting antitoxins and "
            "potions of healing.",
        ),
    }
    for key, (title, summary) in common_items.items():
        nk = normalize_spell_name(key)
        if nk not in index:
            index[nk] = {"kind": "item", "title": title, "summary": summary}

    for c in list_classes(include_faerun=True):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or "")
        label = str(c.get("label") or cid)
        key = normalize_spell_name(cid)
        if key:
            index[key] = {"kind": "class", "title": label, "summary": _class_summary(c)}

    for s in list_species():
        if not isinstance(s, dict):
            continue
        sid = str(s.get("id") or "")
        label = str(s.get("label") or sid)
        key = normalize_spell_name(sid)
        if key:
            index[key] = {"kind": "species", "title": label, "summary": _species_summary(s)}

    for b in list_backgrounds(include_faerun=True):
        if not isinstance(b, dict):
            continue
        bid = str(b.get("id") or "")
        label = str(b.get("label") or bid)
        key = normalize_spell_name(bid)
        if key:
            index[key] = {"kind": "background", "title": label, "summary": _background_summary(b)}

    return index


def _fuzzy_match(name: str, index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    key = normalize_spell_name(name)
    if key in index:
        return index[key]
    # Substring match for compound inventory lines (e.g. "druidic focus (mountain oak staff)")
    if len(key) < 8:
        return None
    best: dict[str, Any] | None = None
    best_len = 0
    for k, entry in index.items():
        if len(k) < 4:
            continue
        if k in key and len(k) > best_len and entry.get("summary"):
            best = entry
            best_len = len(k)
    return best


def _feature_rag_snippet(name: str) -> str | None:
    """Targeted RAG for class features when glossary has no entry."""
    try:
        from backend.rag.engine import retrieve_nodes

        queries = [
            f"LEVEL {name} class feature PHB 2024",
            f'"{name}" class feature',
            f"{name} You can",
        ]
        name_re = re.compile(rf"(?i)\b{re.escape(name)}\b")
        heading_re = re.compile(rf"(?i)LEVEL\s+\d+:\s*{re.escape(name)}\b")
        best: str | None = None
        best_score = 0
        for query in queries:
            nodes = retrieve_nodes(query, top_k=5, factions=["player"], use_rerank=True)
            for n in nodes:
                content = n.node.get_content()
                score = 0
                if heading_re.search(content):
                    score += 100
                elif name_re.search(content):
                    score += 20
                extracted = _extract_feature_section(name, content)
                text = extracted or content
                if score > best_score and len(text.strip()) >= 40:
                    best_score = score
                    best = re.sub(r"\s+", " ", text.strip())[:1200]
        return best
    except Exception:
        return None


def _extract_feature_section(name: str, text: str) -> str | None:
    heading = rf"(?i)LEVEL\s+\d+:\s*{re.escape(name)}\s*\n+(.*?)(?=LEVEL\s+\d+:\s|\Z)"
    m = re.search(heading, text, re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip())
    return None


def _rag_snippet(name: str, *, kind: str = "") -> str | None:
    try:
        from backend.rag.engine import retrieve_nodes

        query = f"{name} D&D 5e 2024 {kind}".strip()
        nodes = retrieve_nodes(query, top_k=1, factions=["player"], use_rerank=False)
        if not nodes:
            nodes = retrieve_nodes(f"{name} spell", top_k=1, factions=["player"], use_rerank=False)
        if not nodes:
            return None
        text = nodes[0].node.get_content().strip()
        text = re.sub(r"\s+", " ", text)
        return text
    except Exception:
        return None


def _feat_lookup_keys(name: str) -> list[str]:
    keys = [normalize_spell_name(name)]
    base = name.split("(")[0].strip()
    if base != name:
        keys.append(normalize_spell_name(base))
    return [k for k in keys if k]


def _scoped_feature_match(name: str, index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    nk = normalize_spell_name(name)
    if not nk:
        return None
    suffix = f"_{nk}"
    matches = {k: v for k, v in index.items() if k.endswith(suffix) and v.get("summary")}
    if len(matches) == 1:
        return next(iter(matches.values()))
    return None


def lookup_entry(name: str, *, use_rag: bool = False, class_id: str = "") -> dict[str, Any]:
    name = (name or "").strip()
    if not name or name == "—":
        return {"kind": "unknown", "title": name, "summary": None}

    index = build_glossary_index()
    candidates = [normalize_spell_name(name)]
    if class_id:
        candidates.insert(0, normalize_spell_name(f"{class_id}_{name}"))
    for key in _feat_lookup_keys(name):
        if key not in candidates:
            candidates.append(key)

    for key in candidates:
        hit = index.get(key)
        if hit and hit.get("summary"):
            return {**hit, "title": hit.get("title") or name}

    hit = _fuzzy_match(name, index)
    if hit and hit.get("summary"):
        return {**hit, "title": hit.get("title") or name}

    hit = _scoped_feature_match(name, index)
    if hit and hit.get("summary"):
        return {**hit, "title": hit.get("title") or name}

    if use_rag:
        feat_snip = _feature_rag_snippet(name)
        if feat_snip:
            return {"kind": "feature", "title": name, "summary": feat_snip}
        for kind in ("spell", "feat", "item", "feature", ""):
            snippet = _rag_snippet(name, kind=kind)
            if snippet:
                return {
                    "kind": "rules",
                    "title": name,
                    "summary": snippet,
                }

    return {
        "kind": "unknown",
        "title": name,
        "summary": None,
    }


def lookup_entries(names: list[str], *, use_rag: bool = False) -> dict[str, dict[str, Any]]:
    return {n: lookup_entry(n, use_rag=use_rag) for n in names if n and n.strip()}


def glossary_payload() -> dict[str, Any]:
    index = build_glossary_index()
    return {
        "count": len(index),
        "entries": index,
    }
