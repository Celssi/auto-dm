"""Extract D&D 5e background mechanics from rulebook PDFs via OCR and/or RAG."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from pypdf import PdfReader

from backend.config import CURATED_DIR, pdf_path
from backend.games.dnd5e.characters.character_data import skills_data
from backend.llm import get_langchain_chat_llm
from backend.rag.engine import query_rules
from backend.rag.ocr import (
    OcrNotAvailableError,
    load_cache,
    load_or_run_ocr,
    needs_ocr,
    tesseract_available,
)
from backend.rag.retrieval_core import get_collection

PDF_KEYS = {
    "player": "dnd5e/player.pdf",
    "heroes_faerun": "dnd5e/heroes_faerun.pdf",
}

BACKGROUND_YAML = {
    "player": CURATED_DIR / "dnd5e_backgrounds.yaml",
    "heroes_faerun": CURATED_DIR / "dnd5e_faerun.yaml",
}

ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")

SKILL_LABEL_TO_ID: dict[str, str] = {
    str(s.get("label", "")).lower(): str(s.get("id", ""))
    for s in (skills_data().get("skills") or [])
    if s.get("label") and s.get("id")
}


@dataclass
class BackgroundSpec:
    id: str
    label: str
    source: str = "player"
    category: str = ""
    ability_scores: list[str] = field(default_factory=list)
    feat: str = ""
    skills: list[str] = field(default_factory=list)
    tool: str = ""
    verified_from_pdf: bool = False

    def to_yaml_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "ability_scores": self.ability_scores,
            "feat": self.feat,
            "skills": self.skills,
            "tool": self.tool,
        }
        if self.source != "player":
            out["source"] = self.source
        if self.category:
            out["category"] = self.category
        return out


def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def load_curated_backgrounds(source: str) -> list[BackgroundSpec]:
    path = BACKGROUND_YAML[source]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("backgrounds") or []
    specs: list[BackgroundSpec] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        specs.append(
            BackgroundSpec(
                id=str(row.get("id") or slugify(str(row.get("label", "")))),
                label=str(row.get("label") or ""),
                source=str(
                    row.get("source") or ("faerun" if source == "heroes_faerun" else "player")
                ),
                category=str(row.get("category") or ""),
                ability_scores=[str(a).lower() for a in (row.get("ability_scores") or [])],
                feat=str(row.get("feat") or ""),
                skills=[str(s).lower() for s in (row.get("skills") or [])],
                tool=str(row.get("tool") or ""),
                verified_from_pdf=bool(row.get("verified_from_pdf")),
            )
        )
    return specs


def _normalize_skill(raw: str) -> str:
    s = raw.strip().lower().replace("-", " ")
    if s in SKILL_LABEL_TO_ID:
        return SKILL_LABEL_TO_ID[s]
    return s.replace(" ", "_")


def _normalize_abilities(raw: list[str]) -> list[str]:
    out: list[str] = []
    for item in raw:
        ab = str(item).strip().lower()[:3]
        if ab in ABILITY_KEYS and ab not in out:
            out.append(ab)
    return out[:3]


def normalize_extracted(data: dict[str, Any]) -> dict[str, Any]:
    skills = [_normalize_skill(s) for s in (data.get("skills") or []) if str(s).strip()]
    skills = [s for s in skills if s]
    return {
        "ability_scores": _normalize_abilities(list(data.get("ability_scores") or [])),
        "feat": str(data.get("feat") or "").strip(),
        "skills": skills[:2],
        "tool": str(data.get("tool") or "").strip(),
        "page": data.get("page"),
        "confidence": str(data.get("confidence") or ""),
    }


def load_pdf_pages(pdf_key: str, *, force_ocr: bool = False) -> list[tuple[int, str]]:
    rel = PDF_KEYS[pdf_key]
    path = pdf_path(rel)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if needs_ocr(path):
        if not tesseract_available():
            cached = load_cache(path)
            if cached:
                return cached
            raise OcrNotAvailableError(
                "PDF requires OCR but Tesseract is not installed. "
                "Install: brew install tesseract — or index PDFs for RAG-only extraction."
            )
        return load_or_run_ocr(path, force=force_ocr)
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((i + 1, text))
    return pages


def _page_context(pages: list[tuple[int, str]], page_no: int, radius: int = 1) -> str:
    by_page = {p: t for p, t in pages}
    chunks: list[str] = []
    for p in range(page_no - radius, page_no + radius + 1):
        if p in by_page:
            chunks.append(f"--- page {p} ---\n{by_page[p]}")
    return "\n\n".join(chunks)


def find_background_pages(pages: list[tuple[int, str]], label: str) -> list[int]:
    """Return page numbers whose text mentions the background title."""
    pattern = re.compile(re.escape(label), re.IGNORECASE)
    loose = re.compile(r"\s+".join(re.escape(w) for w in label.split()), re.IGNORECASE)
    hits: list[int] = []
    for page_no, text in pages:
        if pattern.search(text) or loose.search(text):
            hits.append(page_no)
    return hits


def rag_context_for_background(label: str, *, factions: list[str]) -> str:
    collection = get_collection()
    if collection is None or collection.count() == 0:
        return ""
    question = (
        f"D&D 5e background: {label}. "
        "List ability score options, origin feat, skill proficiencies, and tool proficiency."
    )
    result = query_rules(
        question,
        factions=factions,
        top_k=6,
        use_rerank=True,
        generate_answer=False,
    )
    parts: list[str] = []
    for src in result.sources:
        parts.append(
            f"[{src.get('source_label', '?')} p.{src.get('page', '?')}]\n"
            f"{src.get('text', '')[:2500]}"
        )
    return "\n\n".join(parts)


def parse_background_from_text(
    label: str, context: str, *, provider: str = "claude"
) -> dict[str, Any]:
    llm = get_langchain_chat_llm(provider)  # type: ignore[arg-type]
    system = """You extract D&D 5e (2024) background character-creation data from rulebook text.
Return ONLY valid JSON with keys:
- ability_scores: array of 3 ability abbreviations (str,dex,con,int,wis,cha) the player can boost
- feat: exact origin feat name as printed (e.g. "Magic Initiate (Cleric)")
- skills: array of exactly 2 skill names
- tool: tool proficiency name
- confidence: "high" | "medium" | "low"
Use only what is explicitly supported by the excerpt. Do not invent."""
    user = f"Background: {label}\n\nRulebook excerpt:\n{context[:12000]}"
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError(f"No JSON in LLM response for {label}")
    parsed = json.loads(match.group(0))
    return normalize_extracted(parsed)


def extract_background(
    spec: BackgroundSpec,
    *,
    pdf_key: str,
    pages: list[tuple[int, str]] | None = None,
    use_rag: bool = True,
    use_ocr: bool = True,
    force_ocr: bool = False,
    provider: str = "claude",
) -> dict[str, Any]:
    factions = {
        "player": ["player"],
        "heroes_faerun": ["heroes_faerun", "player"],
    }.get(pdf_key, ["player"])

    contexts: list[str] = []
    page_hint: int | None = None

    if use_rag:
        rag = rag_context_for_background(spec.label, factions=factions)
        if rag.strip():
            contexts.append(rag)

    if use_ocr:
        try:
            if pages is None:
                pages = load_pdf_pages(pdf_key, force_ocr=force_ocr)
            hit_pages = find_background_pages(pages, spec.label)
            if hit_pages:
                page_hint = hit_pages[0]
                contexts.append(_page_context(pages, hit_pages[0], radius=1))
            elif not contexts:
                words = [w for w in spec.label.split() if len(w) > 4]
                if words:
                    for page_no, text in pages:
                        if words[0].lower() in text.lower():
                            contexts.append(_page_context(pages, page_no, radius=0))
                            page_hint = page_no
                            break
        except OcrNotAvailableError:
            if not contexts:
                return {"error": "ocr_unavailable_and_no_rag", "label": spec.label}

    if not contexts:
        return {"error": "no_context", "label": spec.label}

    merged = "\n\n".join(contexts)
    try:
        extracted = parse_background_from_text(spec.label, merged, provider=provider)
        extracted["page"] = page_hint
        src_tags: list[str] = []
        if use_rag and rag_context_for_background(spec.label, factions=factions).strip():
            src_tags.append("rag")
        if page_hint is not None:
            src_tags.append("ocr")
        extracted["sources"] = src_tags or ["text"]
        return extracted
    except Exception as e:
        return {"error": str(e), "label": spec.label}


def _normalize_tool_label(value: str) -> str:
    v = (value or "").strip().lower().replace("’", "'")
    for prefix in ("choose one kind of ", "choose a ", "choose one "):
        if v.startswith(prefix):
            v = v[len(prefix) :]
    return v.strip()


def _normalize_feat_label(value: str) -> str:
    v = (value or "").strip()
    v = re.sub(r"\s*\(see\b.*?\)\s*", "", v, flags=re.IGNORECASE).strip()
    return v.lower()


def diff_background(curated: BackgroundSpec, extracted: dict[str, Any]) -> list[str]:
    if extracted.get("error"):
        return [f"extract failed: {extracted['error']}"]
    diffs: list[str] = []
    for key in ("feat", "tool"):
        c = (getattr(curated, key) or "").strip()
        e = (extracted.get(key) or "").strip()
        if key == "feat":
            if c and e and _normalize_feat_label(c) != _normalize_feat_label(e):
                diffs.append(f"{key}: curated={c!r} pdf={e!r}")
        elif c and e and _normalize_tool_label(c) != _normalize_tool_label(e):
            diffs.append(f"{key}: curated={c!r} pdf={e!r}")
    if curated.skills and extracted.get("skills"):
        if sorted(curated.skills) != sorted(extracted["skills"]):
            diffs.append(f"skills: curated={curated.skills} pdf={extracted['skills']}")
    if curated.ability_scores and extracted.get("ability_scores"):
        if sorted(curated.ability_scores) != sorted(extracted["ability_scores"]):
            diffs.append(
                "ability_scores: "
                f"curated={curated.ability_scores} "
                f"pdf={extracted['ability_scores']}"
            )
    return diffs


def apply_backgrounds_to_yaml(
    source: str,
    updates: list[tuple[BackgroundSpec, dict[str, Any]]],
    *,
    dry_run: bool = True,
) -> Path:
    path = BACKGROUND_YAML[source]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("backgrounds") or []
    by_id = {str(r.get("id")): r for r in rows if isinstance(r, dict)}

    for spec, extracted in updates:
        if extracted.get("error"):
            continue
        row = by_id.get(spec.id)
        if not row:
            row = spec.to_yaml_dict()
            rows.append(row)
            by_id[spec.id] = row
        for key in ("ability_scores", "feat", "skills", "tool"):
            val = extracted.get(key)
            if val:
                row[key] = val
        if extracted.get("page"):
            row["source_page"] = extracted["page"]
        row["verified_from_pdf"] = True

    data["backgrounds"] = rows
    if dry_run:
        out = path.with_suffix(".extracted.preview.yaml")
    else:
        out = path
    out.write_text(
        "# Updated by scripts/extract_backgrounds.py\n"
        + yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return out
