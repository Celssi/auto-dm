"""Audit curated Brambletrek YAML against the Core Rulebook PDF."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml
from pypdf import PdfReader

from backend.config import CURATED_DIR, pdf_path
from backend.rag.ocr import load_or_run_ocr, needs_ocr
from backend.rag.text_utils import clean_text

CORE_PDF_KEY = "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf"
CHARACTER_BANDS = ("ace", "2-4", "5-7", "8-10", "jack", "queen", "king")
RECOVERY_BANDS = ("2-4", "5-7", "8-10", "jack-queen", "king-ace")
JOURNEY_RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace")
JOURNEY_SUITS = ("hearts", "diamonds", "clubs", "spades")
# Per build_brambletrek_modules.py scene table printed pages (CDE).
PUMPKIN_SCENE_PAGES: dict[str, int] = {
    "festival_role": 87,
    "party_companion": 88,
    "choose_adventure": 89,
    "pumpkin_hunt": 90,
    "spirit_catching": 91,
    "costume_contest": 92,
    "pie_tasting": 94,
}
DRAGONKEEP_EXPLORATION_PAGES: dict[str, int] = {
    "path_of_tempest": 64,
    "path_of_pyre": 66,
    "path_of_leaf": 68,
}
SCENE_TABLE_BANDS = ("ace", "2-4", "5-7", "8-10", "jack", "queen", "king")
# Per build_brambletrek_modules.py: one printed page per suit in this order (CDE modules).
JOURNEY_PAGE_SUIT_ORDER = ("hearts", "diamonds", "spades", "clubs")
LEGACY_IDS = ("seer", "scrapper", "storyteller", "seeker", "sneaker", "soother")
OPPONENT_TACTIC_RANKS = (
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "jack",
    "queen",
    "king",
    "ace",
)
_MATCH_STOPWORDS = frozenset(
    {"with", "your", "from", "that", "this", "into", "next", "turn", "the", "and", "for", "you"}
)


@dataclass
class PdfCheck:
    curated_id: str
    printed_page: int
    title: str
    body: str
    label: str = ""


def _load_yaml(name: str) -> dict[str, Any]:
    path = CURATED_DIR / name
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def compact_text(text: str) -> str:
    normalized = text.replace("\u2212", "-").replace("—", "-").replace("–", "-").replace("'", "'")
    return re.sub(r"[^a-z0-9]", "", normalized.lower())


def keyword_ratio(text: str, page_text: str, *, min_ratio: float = 0.55) -> bool:
    words = [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _MATCH_STOPWORDS]
    if not words:
        return False
    page = page_text.lower()
    hits = sum(1 for w in words if w in page)
    return hits / len(words) >= min_ratio


def text_found_in_page(text: str, page_text: str, *, min_chars: int = 36) -> bool:
    """True when curated text matches PDF page (exact prefix or keyword overlap)."""
    if not text.strip() or not page_text.strip():
        return False
    probe = compact_text(text)
    if len(probe) >= min_chars:
        if probe[:min_chars] in compact_text(page_text):
            return True
    elif probe and probe in compact_text(page_text):
        return True
    return keyword_ratio(text, page_text)


def printed_page_to_index(printed_page: int) -> int:
    """Complete Digital Edition: printed book page N is PDF page index N - 2."""
    return max(0, int(printed_page) - 2)


def load_printed_page_text(
    printed_page: int,
    *,
    pdf_key: str = CORE_PDF_KEY,
    force_ocr: bool = False,
) -> str:
    path = pdf_path(pdf_key)
    if not path.exists():
        return ""
    if force_ocr or needs_ocr(path):
        pages = load_or_run_ocr(path, force=force_ocr)
        for page_num, text in pages:
            if page_num == printed_page:
                return clean_text(text)
        return ""
    reader = PdfReader(str(path))
    idx = printed_page_to_index(printed_page)
    if idx < 0 or idx >= len(reader.pages):
        return ""
    return clean_text(reader.pages[idx].extract_text() or "")


def load_module_printed_page_text(
    pdf_key: str,
    printed_page: int,
    *,
    force_ocr: bool = False,
) -> str:
    """Load one printed page from a module PDF (CDE or standalone adventure)."""
    path = pdf_path(pdf_key)
    if not path.exists():
        return ""
    if force_ocr or needs_ocr(path):
        pages = load_or_run_ocr(path, force=force_ocr)
        for page_num, text in pages:
            if page_num == printed_page:
                return clean_text(text)
        return ""
    reader = PdfReader(str(path))
    idx = (
        printed_page_to_index(printed_page)
        if "Complete_Digital" in pdf_key
        else max(0, int(printed_page) - 1)
    )
    if idx < 0 or idx >= len(reader.pages):
        return ""
    return clean_text(reader.pages[idx].extract_text() or "")


def _journey_printed_page(journey_pages: list[Any], suit: str, *, module_id: str = "") -> int:
    """Map a journey suit to its source PDF printed page number."""
    if not journey_pages:
        return 0
    if len(journey_pages) == 2:
        # Winter Gift: p1 = hearts+diamonds, p2 = clubs+spades.
        if suit in ("hearts", "diamonds"):
            return int(journey_pages[0])
        if suit in ("clubs", "spades"):
            return int(journey_pages[1])
    if len(journey_pages) >= 4 and suit in JOURNEY_PAGE_SUIT_ORDER:
        return int(journey_pages[JOURNEY_PAGE_SUIT_ORDER.index(suit)])
    if suit in JOURNEY_SUITS and len(journey_pages) >= len(JOURNEY_SUITS):
        return int(journey_pages[JOURNEY_SUITS.index(suit)])
    return int(journey_pages[0])


def _module_pdf_checks() -> list[PdfCheck]:
    """Verify every curated module row label against its source PDF page."""
    checks: list[PdfCheck] = []
    index = _load_yaml("brambletrek_modules/index.yaml")
    for mid, meta in (index.get("modules") or {}).items():
        if not isinstance(meta, dict):
            continue
        rel = str(meta.get("file") or "")
        data = _load_yaml(f"brambletrek_modules/{rel}") if rel else {}
        source = data.get("source") or {}
        pdf_key = str(source.get("pdf") or "")
        if not pdf_key or not pdf_path(pdf_key).exists():
            continue
        pages = source.get("printed_pages") or {}

        journeys = data.get("journeys") or {}
        if journeys:
            journey_pages = pages.get("journeys") or []
            for suit in JOURNEY_SUITS:
                rows = journeys.get(suit) or {}
                page = _journey_printed_page(journey_pages, suit, module_id=mid)
                for rank, row in rows.items():
                    if not isinstance(row, dict):
                        continue
                    label = str(row.get("label") or row.get("body") or "").strip()
                    if page and label:
                        checks.append(
                            PdfCheck(
                                curated_id=f"module.{mid}.{suit}.{rank}",
                                printed_page=page,
                                title="",
                                body=label[:160],
                                label=label[:120],
                            )
                        )

        if mid == "world_tree":
            reason_page = int(pages.get("reasons") or 0)
            for rank, row in (data.get("reasons") or {}).items():
                if not isinstance(row, dict):
                    continue
                label = str(row.get("title") or row.get("body") or "").strip()
                if reason_page and label:
                    checks.append(
                        PdfCheck(
                            curated_id=f"module.{mid}.reason.{rank}",
                            printed_page=reason_page,
                            title=label[:80],
                            body=str(row.get("body") or label)[:160],
                            label=label[:120],
                        )
                    )

        for table_id, rows in (data.get("scene_tables") or {}).items():
            if not isinstance(rows, dict):
                continue
            page = int(PUMPKIN_SCENE_PAGES.get(table_id) or 0)
            if not page and isinstance(pages.get("scene_tables"), list):
                scene_list = pages.get("scene_tables") or []
                order = list(PUMPKIN_SCENE_PAGES.keys())
                if table_id in order and order.index(table_id) < len(scene_list):
                    page = int(scene_list[order.index(table_id)])
            if not page:
                page = int(pages.get(table_id) or 0)
            for rank, row in rows.items():
                if not isinstance(row, dict):
                    continue
                label = str(row.get("label") or "").strip()
                if page and label:
                    checks.append(
                        PdfCheck(
                            curated_id=f"module.{mid}.{table_id}.{rank}",
                            printed_page=page,
                            title="",
                            body=label[:160],
                            label=label[:120],
                        )
                    )

        expl_pages = pages.get("exploration") or []
        for table_id, rows in (data.get("exploration_tables") or {}).items():
            if not isinstance(rows, dict):
                continue
            page = int(DRAGONKEEP_EXPLORATION_PAGES.get(table_id) or 0)
            if not page and expl_pages:
                order = list(DRAGONKEEP_EXPLORATION_PAGES.keys())
                if table_id in order and order.index(table_id) < len(expl_pages):
                    page = int(expl_pages[order.index(table_id)])
            for rank, row in rows.items():
                if not isinstance(row, dict):
                    continue
                label = str(row.get("label") or row.get("body") or "").strip()
                if page and label:
                    checks.append(
                        PdfCheck(
                            curated_id=f"module.{mid}.{table_id}.{rank}",
                            printed_page=page,
                            title="",
                            body=label[:160],
                            label=label[:120],
                        )
                    )
    return checks


def _character_table_checks() -> list[PdfCheck]:
    data = _load_yaml("brambletrek_character_tables.yaml")
    checks: list[PdfCheck] = []
    page_by_table = {"reasons": 12, "backgrounds": 13, "trinkets": 14}
    for table_key, page in page_by_table.items():
        rows = data.get(table_key) or {}
        for band, row in rows.items():
            if not isinstance(row, dict):
                continue
            checks.append(
                PdfCheck(
                    curated_id=f"{table_key}:{band}",
                    printed_page=page,
                    title=str(row.get("title") or ""),
                    body=str(row.get("body") or ""),
                    label=str(row.get("label") or ""),
                )
            )
    return checks


def _reason_ending_checks() -> list[PdfCheck]:
    data = _load_yaml("brambletrek_reason_endings.yaml")
    checks: list[PdfCheck] = []
    for band, row in (data.get("endings") or {}).items():
        if not isinstance(row, dict):
            continue
        checks.append(
            PdfCheck(
                curated_id=f"reason_ending:{band}",
                printed_page=36,
                title=str(row.get("title") or ""),
                body=str(row.get("body") or ""),
            )
        )
    return checks


def _recovery_label_checks() -> list[PdfCheck]:
    data = _load_yaml("brambletrek_recovery_tables.yaml")
    checks: list[PdfCheck] = []
    for stat, rows in data.items():
        if stat not in ("health", "morale", "supplies") or not isinstance(rows, dict):
            continue
        for band, row in rows.items():
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or "")
            checks.append(
                PdfCheck(
                    curated_id=f"recovery:{stat}:{band}",
                    printed_page=16,
                    title=label,
                    body=label,
                    label=label,
                )
            )
    return checks


def _combat_label_checks() -> list[PdfCheck]:
    data = _load_yaml("brambletrek_combat_reference.yaml")
    checks: list[PdfCheck] = []
    for rank, row in (data.get("opponent_tactics") or {}).items():
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "")
        checks.append(
            PdfCheck(
                curated_id=f"opponent_tactic:{rank}",
                printed_page=30,
                title=label.split("—", 1)[0].strip(),
                body=label,
                label=label,
            )
        )
    return checks


def _journey_spot_checks() -> list[PdfCheck]:
    data = _load_yaml("brambletrek_journey_tables.yaml")
    checks: list[PdfCheck] = []
    page_by_suit = {"hearts": 24, "diamonds": 24, "clubs": 25, "spades": 25}
    for suit in JOURNEY_SUITS:
        rows = data.get(suit) or {}
        for rank in ("2", "ace"):
            row = rows.get(rank)
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or "")
            checks.append(
                PdfCheck(
                    curated_id=f"journey:{suit}:{rank}",
                    printed_page=page_by_suit[suit],
                    title=label,
                    body=label,
                    label=label,
                )
            )
    return checks


def structural_audit() -> list[str]:
    issues: list[str] = []
    tables = _load_yaml("brambletrek_character_tables.yaml")
    endings = _load_yaml("brambletrek_reason_endings.yaml")
    legacies = _load_yaml("brambletrek_legacies.yaml")
    recovery = _load_yaml("brambletrek_recovery_tables.yaml")
    journey = _load_yaml("brambletrek_journey_tables.yaml")
    combat = _load_yaml("brambletrek_combat_reference.yaml")

    for table_key in ("reasons", "backgrounds", "trinkets"):
        rows = tables.get(table_key) or {}
        for band in CHARACTER_BANDS:
            row = rows.get(band)
            if not isinstance(row, dict):
                issues.append(f"character_tables.{table_key} missing band {band}")
                continue
            for field in ("label", "title", "body"):
                if not str(row.get(field) or "").strip():
                    issues.append(f"character_tables.{table_key}.{band} missing {field}")

    reason_titles = {
        band: str((tables.get("reasons") or {}).get(band, {}).get("title") or "")
        for band in CHARACTER_BANDS
    }
    for band, row in (endings.get("endings") or {}).items():
        if band not in CHARACTER_BANDS:
            issues.append(f"reason_endings unknown band {band}")
            continue
        if not isinstance(row, dict):
            issues.append(f"reason_endings.{band} not a dict")
            continue
        ending_title = str(row.get("title") or "").strip()
        reason_title = reason_titles.get(band, "").strip()
        if ending_title and reason_title and ending_title != reason_title:
            issues.append(
                f"reason_endings.{band} title {ending_title!r} != reason title {reason_title!r}"
            )
        if not str(row.get("body") or "").strip():
            issues.append(f"reason_endings.{band} missing body")

    legacy_rows = legacies.get("legacies") or {}
    if not legacies.get("overcome_the_odds"):
        issues.append("legacies missing overcome_the_odds")
    for legacy_id in LEGACY_IDS:
        row = legacy_rows.get(legacy_id)
        if not isinstance(row, dict):
            issues.append(f"legacies missing {legacy_id}")
            continue
        abilities = row.get("abilities") or []
        if len(abilities) != 4:
            issues.append(f"legacies.{legacy_id} expected 4 abilities, got {len(abilities)}")

    for stat in ("health", "morale", "supplies"):
        rows = recovery.get(stat) or {}
        for band in RECOVERY_BANDS:
            row = rows.get(band)
            if not isinstance(row, dict) or not str(row.get("label") or "").strip():
                issues.append(f"recovery_tables.{stat} missing band {band}")

    for suit in JOURNEY_SUITS:
        rows = journey.get(suit) or {}
        for rank in JOURNEY_RANKS:
            row = rows.get(rank)
            if not isinstance(row, dict) or not str(row.get("label") or "").strip():
                issues.append(f"journey_tables.{suit} missing rank {rank}")

    tactic_rows = combat.get("opponent_tactics") or {}
    for rank in OPPONENT_TACTIC_RANKS:
        row = tactic_rows.get(rank)
        if not isinstance(row, dict) or not str(row.get("label") or "").strip():
            issues.append(f"combat_reference.opponent_tactics missing rank {rank}")

    issues.extend(_module_structural_audit())
    return issues


def _module_structural_audit() -> list[str]:
    """Validate per-adventure module YAML under brambletrek_modules/."""
    issues: list[str] = []
    index = _load_yaml("brambletrek_modules/index.yaml")
    modules = index.get("modules") or {}
    expected = {
        "world_tree",
        "dragonkeep",
        "pumpkin_party",
        "first_frost",
        "birthday_wonders",
        "winter_gift",
    }
    for mid in expected:
        if mid not in modules:
            issues.append(f"brambletrek_modules.index missing {mid}")
    for mid, meta in modules.items():
        if not isinstance(meta, dict):
            continue
        rel = str(meta.get("file") or "").strip()
        if not rel:
            issues.append(f"brambletrek_modules.{mid} missing file")
            continue
        data = _load_yaml(f"brambletrek_modules/{rel}")
        if not data:
            issues.append(f"brambletrek_modules/{rel} empty or missing")
            continue
        journeys = data.get("journeys") or {}
        scenes = data.get("scene_tables") or {}
        exploration = data.get("exploration_tables") or {}
        if journeys:
            min_rows = 13 if mid == "winter_gift" else 10
            for suit in JOURNEY_SUITS:
                rows = journeys.get(suit) or {}
                if len(rows) < min_rows:
                    issues.append(f"module.{mid}.journeys.{suit} only {len(rows)} rows")
        elif scenes.get("choose_adventure"):
            for suit in JOURNEY_SUITS:
                row = (scenes.get("choose_adventure") or {}).get(suit)
                if not isinstance(row, dict) or not row.get("scene_table"):
                    issues.append(f"module.{mid}.choose_adventure missing suit {suit}")
        elif exploration:
            for table_id, rows in exploration.items():
                if not isinstance(rows, dict) or len(rows) < 5:
                    issues.append(
                        f"module.{mid}.exploration.{table_id} only {len(rows or {})} rows"
                    )
        else:
            issues.append(f"module.{mid} has no journeys, scene_tables, or exploration_tables")
        if mid == "world_tree":
            reasons = data.get("reasons") or {}
            if len(reasons) != 13:
                issues.append(f"module.world_tree reasons expected 13 ranks, got {len(reasons)}")
            combat = data.get("combat") or {}
            guardians = combat.get("guardians") or {}
            for suit in ("hearts", "diamonds"):
                rows = guardians.get(suit) or {}
                if len(rows) != 13:
                    issues.append(
                        f"module.world_tree.combat.guardians.{suit} expected 13, got {len(rows)}"
                    )
        if mid == "pumpkin_party":
            scene_tables = data.get("scene_tables") or {}
            for table_id in ("pumpkin_hunt", "spirit_catching", "costume_contest", "pie_tasting"):
                rows = scene_tables.get(table_id) or {}
                if len(rows) < 10:
                    issues.append(f"module.pumpkin_party.{table_id} only {len(rows)} ranks")
        if mid == "first_frost":
            scenes = data.get("scene_tables") or {}
            snacker = scenes.get("snacker_tactics") or {}
            if snacker:
                ace = snacker.get("ace") or {}
                if ace.get("combat"):
                    issues.append(
                        "module.first_frost.snacker_tactics.ace has erroneous combat flag"
                    )
        if mid == "winter_gift":
            scenes = data.get("scene_tables") or {}
            surveyor = scenes.get("surveyor_tactics") or {}
            if surveyor:
                ace = surveyor.get("ace") or {}
                if ace.get("combat"):
                    issues.append(
                        "module.winter_gift.surveyor_tactics.ace has erroneous combat flag"
                    )
        if mid == "dragonkeep":
            combat = data.get("combat") or {}
            opponents = combat.get("opponents") or {}
            if len(opponents) < 9:
                issues.append(
                    f"module.dragonkeep.combat.opponents expected 9+, got {len(opponents)}"
                )
            for path in ("path_of_tempest", "path_of_pyre", "path_of_leaf"):
                mapping = (combat.get("opponent_by_rank") or {}).get(path) or {}
                if len(mapping) < 3:
                    issues.append(f"module.dragonkeep.opponent_by_rank.{path} expected 3+ ranks")
            eolan = combat.get("eolan") or {}
            for step in ("antechamber", "door", "finale"):
                if not isinstance(eolan.get(step), dict):
                    issues.append(f"module.dragonkeep.eolan missing {step}")
            phases = eolan.get("aerith_phases") or {}
            for phase in ("1", "2", "3"):
                pdata = phases.get(phase) or {}
                if len(pdata.get("aerith_tactics") or {}) < 7:
                    issues.append(f"module.dragonkeep.aerith phase {phase} tactics incomplete")
                if len(pdata.get("items") or {}) < 7:
                    issues.append(f"module.dragonkeep.aerith phase {phase} items incomplete")
                if not pdata.get("damage_goal") or not pdata.get("rounds_goal"):
                    issues.append(f"module.dragonkeep.aerith phase {phase} missing phase goals")
            exploration = data.get("exploration_tables") or {}
            for path_id in ("path_of_tempest", "path_of_pyre", "path_of_leaf"):
                rows = exploration.get(path_id) or {}
                for rk in ("jack", "queen", "king"):
                    if rk not in rows:
                        issues.append(f"module.dragonkeep.exploration.{path_id} missing {rk}")
    return issues


def pdf_audit(*, limit: int = 0, force_ocr: bool = False) -> list[str]:
    if not pdf_path(CORE_PDF_KEY).exists():
        return [f"Core PDF missing: {CORE_PDF_KEY}"]

    checks = (
        _character_table_checks()
        + _reason_ending_checks()
        + _recovery_label_checks()
        + _combat_label_checks()
        + _journey_spot_checks()
        + _module_pdf_checks()
    )
    if limit > 0:
        checks = checks[:limit]

    page_cache: dict[tuple[str, int], str] = {}
    issues: list[str] = []
    total = len(checks)
    for i, check in enumerate(checks, 1):
        pdf_key = CORE_PDF_KEY
        if check.curated_id.startswith("module."):
            mid = check.curated_id.split(".")[1]
            mod_index = _load_yaml("brambletrek_modules/index.yaml")
            rel = str(((mod_index.get("modules") or {}).get(mid, {}) or {}).get("file") or "")
            mod = _load_yaml(f"brambletrek_modules/{rel}") if rel else {}
            pdf_key = str((mod.get("source") or {}).get("pdf") or CORE_PDF_KEY)
        cache_key = (pdf_key, check.printed_page)
        if cache_key not in page_cache:
            if check.curated_id.startswith("module."):
                page_cache[cache_key] = load_module_printed_page_text(
                    pdf_key, check.printed_page, force_ocr=force_ocr
                )
            else:
                page_cache[cache_key] = load_printed_page_text(
                    check.printed_page, force_ocr=force_ocr
                )
        page_text = page_cache[cache_key]
        if not page_text.strip():
            issues.append(
                f"{check.curated_id}: no text on p.{check.printed_page} "
                f"(PDF index {printed_page_to_index(check.printed_page) + 1})"
            )
            print(f"  [{i}/{total}] {check.curated_id} — empty page", flush=True)
            continue

        title_ok = not check.title or text_found_in_page(check.title, page_text, min_chars=12)
        body_ok = text_found_in_page(check.body, page_text, min_chars=24)
        if body_ok or (title_ok and compact_text(check.body) == compact_text(check.title)):
            print(f"  [{i}/{total}] {check.curated_id} — OK", flush=True)
            continue

        print(f"  [{i}/{total}] {check.curated_id} — mismatch", flush=True)
        if not title_ok and not body_ok:
            if not title_ok:
                issues.append(
                    f"{check.curated_id}: title not found on p.{check.printed_page}: {check.title!r}"
                )
            if not body_ok:
                issues.append(
                    f"{check.curated_id}: body/label not found on p.{check.printed_page} "
                    f"({check.label or check.body[:48]!r}…)"
                )
        elif not body_ok:
            issues.append(
                f"{check.curated_id}: body/label not found on p.{check.printed_page} "
                f"({check.label or check.body[:48]!r}…)"
            )
        elif not title_ok:
            issues.append(
                f"{check.curated_id}: title not found on p.{check.printed_page}: {check.title!r}"
            )
    return issues


def run_curated_audit(*, skip_pdf: bool = False, limit: int = 0, force_ocr: bool = False) -> int:
    """Run structural + optional PDF checks. Returns 0 when clean, 1 when issues found."""
    print("=== Brambletrek structural audit ===")
    struct_issues = structural_audit()
    if struct_issues:
        print(f"Structural issues ({len(struct_issues)}):")
        for issue in struct_issues:
            print(f"  - {issue}")
    else:
        print("Structural checks: OK")

    if skip_pdf:
        return 1 if struct_issues else 0

    print("\n=== Brambletrek PDF audit (Complete Digital Edition) ===")
    pdf_issues = pdf_audit(limit=limit, force_ocr=force_ocr)
    if pdf_issues:
        print(f"\nPDF mismatches ({len(pdf_issues)}):")
        for issue in pdf_issues:
            print(f"  - {issue}")
    else:
        print("\nPDF checks: OK")

    return 1 if (struct_issues or pdf_issues) else 0
