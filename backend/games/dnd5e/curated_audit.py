"""Audit curated D&D 5e YAML against PHB PDFs and internal consistency."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from backend.config import CURATED_DIR, pdf_path
from backend.games.brambletrek.curated_audit import (
    PdfCheck,
    compact_text,
    text_found_in_page,
)
from backend.games.dnd5e.characters.background_extract import (
    diff_background,
    extract_background,
    load_curated_backgrounds,
    load_pdf_pages,
)
from backend.games.dnd5e.characters.character_builder import _weapon_catalog_row, _weapon_dicts
from backend.games.dnd5e.characters.character_data import (
    equipment_data,
    get_armor,
    get_background,
    get_weapon,
    list_backgrounds,
    list_classes,
    list_species,
    list_starting_gear_options,
    list_weapons,
)
from backend.games.dnd5e.characters.features import class_features_data, subclass_features_data

PLAYER_PDF_KEY = "dnd5e/player.pdf"
# PHB 2024 printed pages (character creation / equipment chapter).
BACKGROUND_START_PAGE = 180
CLASS_SPOT_PAGES: dict[str, int] = {
    "fighter": 102,
    "wizard": 119,
    "rogue": 128,
}
SPECIES_SPOT_PAGES: dict[str, int] = {
    "human": 194,
    "elf": 196,
}
EQUIPMENT_PAGE = 214
FIGHTING_STYLE_PAGE = 202


def load_phb_page_text(printed_page: int, *, force_ocr: bool = False) -> str:
    """Load one printed PHB page (book page number from OCR cache)."""
    from pypdf import PdfReader

    from backend.config import OCR_CACHE_DIR
    from backend.rag.ocr import load_or_run_ocr, needs_ocr
    from backend.rag.text_utils import clean_text

    path = pdf_path(PLAYER_PDF_KEY)
    if not path.exists():
        return ""

    cache = OCR_CACHE_DIR / "player.json"
    if cache.exists() and not force_ocr:
        import json

        data = json.loads(cache.read_text(encoding="utf-8"))
        for row in data.get("pages") or []:
            if int(row.get("page") or 0) == int(printed_page):
                return clean_text(str(row.get("text") or ""))

    if force_ocr or needs_ocr(path):
        for page_num, text in load_or_run_ocr(path, force=force_ocr):
            if page_num == printed_page:
                return clean_text(text)
        return ""

    reader = PdfReader(str(path))
    idx = max(0, int(printed_page) - 1)
    if idx >= len(reader.pages):
        return ""
    return clean_text(reader.pages[idx].extract_text() or "")


@dataclass
class StructuralCounts:
    classes: int = 12
    species: int = 10
    backgrounds: int = 16


def _load_yaml(name: str) -> dict[str, Any]:
    path = CURATED_DIR / name
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _glossary_entry(entry_id: str) -> dict[str, Any]:
    glossary = _load_yaml("dnd5e_glossary.yaml").get("entries") or {}
    row = glossary.get(entry_id) or {}
    return row if isinstance(row, dict) else {}


def equipment_consistency_audit() -> list[str]:
    """Package weapons/armor must match equipment catalog."""
    issues: list[str] = []
    gs = get_weapon("greatsword")
    if not gs or str(gs.get("damage")) != "2d6":
        issues.append("equipment.greatsword catalog damage must be 2d6")

    gear_opts = equipment_data().get("class_starting_gear_options") or {}
    for class_id in gear_opts:
        for package in list_starting_gear_options(class_id):
            pkg_id = str(package.get("id") or "")
            for weapon in package.get("weapons") or []:
                if not isinstance(weapon, dict):
                    continue
                name = str(weapon.get("name") or "")
                catalog = _weapon_catalog_row(name)
                if not catalog:
                    issues.append(f"equipment.{class_id}.{pkg_id}: unknown weapon {name!r}")
                    continue
                built = _weapon_dicts([weapon])[0]
                if built["damage"] != str(catalog.get("damage")):
                    issues.append(
                        f"equipment.{class_id}.{pkg_id}: {name} damage "
                        f"{built['damage']} != catalog {catalog.get('damage')}"
                    )
            armor_id = str(package.get("armor") or "")
            if armor_id and armor_id not in ("", "none") and not get_armor(armor_id):
                issues.append(f"equipment.{class_id}.{pkg_id}: unknown armor {armor_id!r}")

    for weapon in list_weapons():
        wid = str(weapon.get("id") or "")
        damage = str(weapon.get("damage") or "")
        if not damage or not re.match(r"^\d+d\d+(\+\d+)?$", damage.replace(" ", "")):
            issues.append(f"equipment.weapon.{wid}: invalid damage {damage!r}")
    return issues


def structural_audit(*, counts: StructuralCounts | None = None) -> list[str]:
    """Counts, subclass keys, gear consistency across dnd5e_*.yaml."""
    counts = counts or StructuralCounts()
    issues: list[str] = []

    core_classes = list_classes(include_faerun=False)
    if len(core_classes) != counts.classes:
        issues.append(f"Expected {counts.classes} PHB classes, got {len(core_classes)}")
    if len(list_species()) != counts.species:
        issues.append(f"Expected {counts.species} PHB species, got {len(list_species())}")
    if len(list_backgrounds(include_faerun=False)) != counts.backgrounds:
        issues.append(
            f"Expected {counts.backgrounds} PHB backgrounds, "
            f"got {len(list_backgrounds(include_faerun=False))}"
        )

    for cls in core_classes:
        cid = cls["id"]
        if not cls.get("hit_die"):
            issues.append(f"Class {cid} missing hit_die")
        if not cls.get("subclasses"):
            issues.append(f"Class {cid} missing subclasses")
        cf = (class_features_data().get("classes") or {}).get(cid)
        if not cf:
            issues.append(f"Class {cid} missing class_features entry")
        subs = subclass_features_data().get("subclasses") or {}
        sub_labels = {
            str(v.get("label", ""))
            for v in subs.values()
            if isinstance(v, dict) and v.get("class_id") == cid
        }
        for sub in cls.get("subclasses") or []:
            if sub not in sub_labels:
                issues.append(f"Subclass feature missing: {cid} / {sub}")

    for bg in list_backgrounds(include_faerun=False):
        row = get_background(bg["id"])
        if not row:
            issues.append(f"Background {bg['id']} not loadable")
            continue
        for key in ("feat", "skills", "tool", "ability_scores"):
            if not row.get(key):
                issues.append(f"Background {bg['id']} missing {key}")

    issues.extend(equipment_consistency_audit())

    defense = _glossary_entry("defense")
    if defense and "+1 bonus to Armor Class" not in str(defense.get("text") or ""):
        issues.append("glossary.defense missing +1 AC text")

    creation = _load_yaml("dnd5e_creation_choices.yaml")
    fighter_styles = creation.get("fighting_style_feats") or []
    style_ids = {str(s.get("id") or "") for s in fighter_styles if isinstance(s, dict)}
    if "defense" not in style_ids:
        issues.append("creation_choices missing defense fighting style")

    return issues


def _pdf_spot_checks() -> list[PdfCheck]:
    checks: list[PdfCheck] = []
    defense = _glossary_entry("defense")
    checks.append(
        PdfCheck(
            curated_id="fighting_style.defense",
            printed_page=FIGHTING_STYLE_PAGE,
            title=str(defense.get("title") or "Defense"),
            body=str(defense.get("text") or "")[:120],
            label="+1 AC while wearing armor",
        )
    )
    gs = get_weapon("greatsword") or {}
    checks.append(
        PdfCheck(
            curated_id="equipment.greatsword",
            printed_page=EQUIPMENT_PAGE,
            title=str(gs.get("label") or "Greatsword"),
            body="2d6",
            label="greatsword damage 2d6",
        )
    )
    for class_id, page in CLASS_SPOT_PAGES.items():
        cls = next((c for c in list_classes(include_faerun=False) if c["id"] == class_id), None)
        if not cls:
            continue
        checks.append(
            PdfCheck(
                curated_id=f"class.{class_id}",
                printed_page=page,
                title=str(cls.get("label") or class_id),
                body=str(cls.get("label") or class_id),
                label=f"class spot {class_id}",
            )
        )
    for species_id, page in SPECIES_SPOT_PAGES.items():
        sp = next((s for s in list_species() if s["id"] == species_id), None)
        if not sp:
            continue
        checks.append(
            PdfCheck(
                curated_id=f"species.{species_id}",
                printed_page=page,
                title=str(sp.get("label") or species_id),
                body=str(sp.get("label") or species_id),
                label=f"species spot {species_id}",
            )
        )
    return checks


def pdf_background_audit(*, limit: int = 0, force_ocr: bool = False) -> list[str]:
    if not pdf_path(PLAYER_PDF_KEY).exists():
        return [f"PHB PDF missing: {PLAYER_PDF_KEY}"]

    issues: list[str] = []
    specs = load_curated_backgrounds("player")
    if limit > 0:
        specs = specs[:limit]
    pages = load_pdf_pages("player", force_ocr=force_ocr)
    total = len(specs)
    for i, spec in enumerate(specs, 1):
        if spec.verified_from_pdf:
            print(f"  [{i}/{total}] {spec.label} — skip (verified_from_pdf)", flush=True)
            continue
        print(f"  [{i}/{total}] {spec.label}...", flush=True)
        extracted = extract_background(
            spec,
            pdf_key="player",
            pages=pages,
            use_rag=True,
            use_ocr=True,
            force_ocr=force_ocr,
        )
        diffs = diff_background(spec, extracted)
        if extracted.get("error"):
            issues.append(f"[player] {spec.label}: extract error — {extracted['error']}")
            print(f"       error: {extracted['error']}", flush=True)
        elif diffs:
            print(f"       {len(diffs)} mismatch(es)", flush=True)
        else:
            print("       OK", flush=True)
        for diff in diffs:
            issues.append(f"[player] {spec.label}: {diff}")
    return issues


def pdf_spot_audit(*, limit: int = 0, force_ocr: bool = False) -> list[str]:
    if not pdf_path(PLAYER_PDF_KEY).exists():
        return [f"PHB PDF missing: {PLAYER_PDF_KEY}"]

    checks = _pdf_spot_checks()
    if limit > 0:
        checks = checks[:limit]

    page_cache: dict[int, str] = {}
    issues: list[str] = []
    total = len(checks)
    for i, check in enumerate(checks, 1):
        if check.printed_page not in page_cache:
            page_cache[check.printed_page] = load_phb_page_text(
                check.printed_page,
                force_ocr=force_ocr,
            )
        page_text = page_cache[check.printed_page]
        if not page_text.strip():
            issues.append(f"{check.curated_id}: no text on p.{check.printed_page}")
            print(f"  [{i}/{total}] {check.curated_id} — empty page", flush=True)
            continue

        title_ok = not check.title or text_found_in_page(check.title, page_text, min_chars=8)
        body_ok = text_found_in_page(check.body, page_text, min_chars=3)
        if body_ok or title_ok:
            print(f"  [{i}/{total}] {check.curated_id} — OK", flush=True)
            continue

        print(f"  [{i}/{total}] {check.curated_id} — mismatch", flush=True)
        if not body_ok:
            issues.append(
                f"{check.curated_id}: {check.label} not found on p.{check.printed_page}"
            )
        elif not title_ok:
            issues.append(
                f"{check.curated_id}: title not found on p.{check.printed_page}: {check.title!r}"
            )
    return issues


def pdf_audit(*, limit: int = 0, force_ocr: bool = False) -> list[str]:
    issues = pdf_spot_audit(limit=limit, force_ocr=force_ocr)
    if limit == 0:
        issues.extend(pdf_background_audit(force_ocr=force_ocr))
    return issues


def run_curated_audit(*, skip_pdf: bool = False, limit: int = 0, force_ocr: bool = False) -> int:
    """Run structural + optional PDF checks. Returns 0 when clean, 1 when issues found."""
    print("=== D&D 5e structural audit ===")
    struct_issues = structural_audit()
    if struct_issues:
        print(f"Structural issues ({len(struct_issues)}):")
        for issue in struct_issues:
            print(f"  - {issue}")
    else:
        print("Structural checks: OK")

    if skip_pdf:
        return 1 if struct_issues else 0

    if not pdf_path(PLAYER_PDF_KEY).exists():
        print(f"\nPHB PDF missing ({PLAYER_PDF_KEY}); skipping PDF audit")
        return 1 if struct_issues else 0

    print("\n=== D&D 5e PDF spot audit (player.pdf) ===")
    pdf_issues = pdf_audit(limit=limit, force_ocr=force_ocr)
    if pdf_issues:
        print(f"\nPDF mismatches ({len(pdf_issues)}):")
        for issue in pdf_issues:
            print(f"  - {issue}")
    else:
        print("\nPDF checks: OK")

    return 1 if (struct_issues or pdf_issues) else 0
