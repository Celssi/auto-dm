"""Brambletrek retrieval helpers."""

from __future__ import annotations

import re
from typing import Any

from llama_index.core.schema import NodeWithScore, TextNode

from backend.rag.retrieval_core import get_lexical_corpus

_PRIMARY_RULEBOOK_SUFFIX = "Brambletrek_-_Complete_Digital_Edition.pdf"

# Printed book page numbers (as referenced in shortcuts/curated YAML).
# Mapped to PDF page indices in Complete Digital Edition via _brambletrek_pdf_page().
_BRAMBLETREK_TABLE_PAGES: dict[str, list[int]] = {
    "reason": [12],
    "background": [13],
    "trinket": [14],
    "resources": [8, 15, 16],
    "legacy": [9, 17, 18, 19, 20, 21],
    "journey": [24, 25, 26],
    "combat": [30, 31],
    "recovery": [16],
    "ending": [36],
}

# Table pages before intro/legacy overview when injecting creation context.
_BRAMBLETREK_PAGE_ORDER = [24, 25, 12, 13, 14, 15, 16, 8, 9, 17, 18, 19, 20, 21, 26, 30, 31, 36]


def _brambletrek_pdf_page(printed_page: int) -> int:
    """Convert rulebook printed page number to PDF index in Complete Digital Edition."""
    return max(1, int(printed_page) - 1)


def _brambletrek_page_sort_key(page: int) -> tuple[int, int]:
    try:
        return (_BRAMBLETREK_PAGE_ORDER.index(page), page)
    except ValueError:
        return (len(_BRAMBLETREK_PAGE_ORDER), page)


def _is_brambletrek_journey_question(question: str) -> bool:
    lower = question.lower()
    if any(
        term in lower
        for term in (
            "journey & exploration",
            "journey and exploration",
            "journey day",
            "exploration day",
            "today's journey",
            "four cards",
            "4 cards",
            "event 1",
            "clubs spades",
            "hearts diamonds",
        )
    ):
        return True
    if "journey" in lower and any(w in lower for w in ("exploration", "event", "draw order")):
        return True
    return False


def _is_brambletrek_ending_question(question: str) -> bool:
    lower = question.lower()
    return any(
        term in lower
        for term in (
            "story ending",
            "reason ending",
            "reason's ending",
            "your reason's ending",
            "end my journey",
            "end my story",
            "how does my story end",
            "how does my adventure end",
            "page 36",
            "true ending",
            "finish my journey",
        )
    )


def _is_brambletrek_adventure_question(question: str) -> bool:
    lower = question.lower()
    if any(
        name in lower
        for name in (
            "birthday of wonders",
            "pumpkin party",
            "first frost",
            "warmth of the first frost",
            "winter gift",
            "adventure module",
            "adventure act",
            "adventure scene",
        )
    ):
        return True
    return "adventure" in lower and any(
        w in lower for w in ("act", "scene", "module", "campaign", "quest")
    )


def _is_brambletrek_character_creation(question: str) -> bool:
    lower = question.lower()
    if "random gnawborn" in lower or "character creation" in lower:
        return True
    table_hits = sum(
        1 for term in ("reason for adventure", "background", "trinket") if term in lower
    )
    return table_hits >= 2 and ("resource" in lower or "legacy" in lower)


def _is_brambletrek_adventure_scene_prompt(question: str) -> bool:
    lower = question.lower()
    return "adventure scene" in lower or "adventure module text in the indexed pdf" in lower


def _brambletrek_tables_needed(
    question: str,
    brambletrek_character: Any = None,
) -> set[str]:
    lower = question.lower()
    needed: set[str] = set()
    adv_id = getattr(brambletrek_character, "active_adventure", "") if brambletrek_character else ""
    if any(
        term in lower
        for term in ("reason for adventure", "reason table", "reason:", "reason for my")
    ):
        needed.add("reason")
    if "background" in lower:
        needed.add("background")
    if "trinket" in lower:
        needed.add("trinket")
    if any(
        term in lower
        for term in (
            "resource",
            "health, morale",
            "morale, and supplies",
            "six resource",
            "six cards",
            "two cards per stat",
            "character resources",
        )
    ):
        needed.add("resources")
    if "legacy" in lower or any(
        name in lower
        for name in ("seer", "scrapper", "storyteller", "seeker", "sneaker", "soother")
    ):
        needed.add("legacy")
    if _is_brambletrek_journey_question(question):
        skip_journey = adv_id and (
            _is_brambletrek_adventure_scene_prompt(question)
            or _is_brambletrek_adventure_question(question)
        )
        if not skip_journey:
            needed.add("journey")
    if any(term in lower for term in ("combat setup", "initiative", "tactic card", "tactics")):
        needed.add("combat")
    if any(term in lower for term in ("health recovery", "morale recovery", "supplies recovery")):
        needed.add("recovery")
    if _is_brambletrek_ending_question(question):
        needed.add("ending")
    if _is_brambletrek_character_creation(question):
        needed |= set(_BRAMBLETREK_TABLE_PAGES.keys())
    return needed


def _is_brambletrek_card_question(question: str) -> bool:
    if _brambletrek_tables_needed(question):
        return True
    lower = question.lower()
    rank_words = ("ace", "jack", "queen", "king")
    suit_words = ("spade", "spades", "heart", "hearts", "club", "clubs", "diamond", "diamonds")
    has_rank_or_value = any(w in lower for w in rank_words) or bool(
        re.search(r"\b(10|[2-9])\b", lower)
    )
    has_card_terms = "card" in lower or any(w in lower for w in suit_words)
    has_reason_terms = "reason for adventure" in lower or "reason table" in lower
    return (has_rank_or_value and has_card_terms) or has_reason_terms


def _enhance_brambletrek_query(
    question: str,
    brambletrek_character: Any = None,
) -> str:
    if _is_brambletrek_ending_question(question):
        return (
            f"{question} your reason's ending page 36 reason ending true ending "
            "continue story within Hyhill open-ended"
        )
    if brambletrek_character and getattr(brambletrek_character, "active_adventure", ""):
        from backend.games.brambletrek.dm.curated import adventure_meta

        adv = adventure_meta(brambletrek_character.active_adventure)
        label = adv.get("label", "")
        if label:
            question = f"{question} {label} adventure module"
    if _is_brambletrek_journey_question(question):
        adv_id = (
            getattr(brambletrek_character, "active_adventure", "") if brambletrek_character else ""
        )
        if adv_id and (
            _is_brambletrek_adventure_scene_prompt(question)
            or _is_brambletrek_adventure_question(question)
        ):
            from backend.games.brambletrek.dm.curated import adventure_meta

            adv = adventure_meta(adv_id)
            label = adv.get("label", "")
            return f"{question} {label} adventure scene module PDF indexed"
        return (
            f"{question} journey and exploration four cards draw order hearts diamonds "
            "clubs spades page 24 page 25 aldwund depths page 26 page 27 exit item combat"
        )
    if _is_brambletrek_character_creation(question):
        return (
            f"{question} reason for adventure background trinket character resources legacy "
            "core rulebook pages 8 12 13 14 15 16 card value ace 2-4 5-7 8-10 jack queen king "
            "maximum 20 two cards per stat"
        )
    if not _is_brambletrek_card_question(question):
        return question
    extras = "reason for adventure card value reason table character creation ace 2-4 5-7 8-10 jack queen king"
    if "background" in question.lower():
        extras += " background table card value"
    if "trinket" in question.lower():
        extras += " trinket table card value"
    if "resource" in question.lower():
        extras += " character resources health morale supplies six cards maximum 20"
    return f"{question} {extras}"


def _brambletrek_prompt_top_k(
    question: str,
    top_k: int,
    brambletrek_character: Any = None,
) -> int:
    needed = _brambletrek_tables_needed(question, brambletrek_character)
    if not needed:
        return max(top_k, 6)
    return max(top_k, min(22, top_k + len(needed) * 4))


def _brambletrek_core_page_nodes(
    game_id: str,
    collection,
    printed_pages: set[int],
) -> list[NodeWithScore]:
    """Inject chunks from Complete Digital Edition by printed rulebook page."""
    pdf_pages = {_brambletrek_pdf_page(p) for p in printed_pages}
    docs, metas = get_lexical_corpus(game_id, collection)
    nodes: list[NodeWithScore] = []
    for text, meta in zip(docs, metas):
        if not text or not meta:
            continue
        if str(meta.get("faction", "")).lower() != "core":
            continue
        if not str(meta.get("source_file", "")).endswith(_PRIMARY_RULEBOOK_SUFFIX):
            continue
        try:
            page = int(meta.get("page", 0))
        except (TypeError, ValueError):
            continue
        if page not in pdf_pages:
            continue
        nodes.append(
            NodeWithScore(
                node=TextNode(text=str(text), metadata=meta),
                score=250.0 - page,
            )
        )
    nodes.sort(
        key=lambda n: (
            _brambletrek_page_sort_key(int((n.node.metadata or {}).get("page", 0) or 0) + 1),
            n.get_content()[:80],
        )
    )
    return nodes


def _brambletrek_creation_table_nodes(
    game_id: str,
    collection,
    question: str,
    brambletrek_character: Any = None,
) -> list[NodeWithScore]:
    needed = _brambletrek_tables_needed(question, brambletrek_character)
    if not needed:
        return []
    pages: set[int] = set()
    for table in needed:
        pages.update(_BRAMBLETREK_TABLE_PAGES.get(table, []))
    return _brambletrek_core_page_nodes(game_id, collection, pages)


def _brambletrek_adventure_module_nodes(
    game_id: str,
    collection,
    adventure_id: str,
    *,
    limit: int = 10,
) -> list[NodeWithScore]:
    from backend.games.brambletrek.dm.curated import adventure_meta

    meta = adventure_meta(adventure_id)
    source_label = str(meta.get("source_label", "") or "").strip()
    if not source_label:
        return []
    page_min = meta.get("pdf_page_min")
    page_max = meta.get("pdf_page_max")
    docs, metas = get_lexical_corpus(game_id, collection)
    nodes: list[NodeWithScore] = []
    for text, meta_row in zip(docs, metas):
        if not text or not meta_row:
            continue
        if str(meta_row.get("source_label", "")) != source_label:
            continue
        if page_min is not None and page_max is not None:
            try:
                p = int(meta_row.get("page", 0) or 0)
            except (TypeError, ValueError):
                continue
            if p < int(page_min) or p > int(page_max):
                continue
        nodes.append(
            NodeWithScore(
                node=TextNode(text=text, metadata=dict(meta_row)),
                score=1.0,
            )
        )
    nodes.sort(key=lambda n: int((n.node.metadata or {}).get("page", 0) or 0))
    return nodes[:limit]


def _brambletrek_reason_table_nodes(
    game_id: str,
    collection,
    limit: int = 8,
) -> list[NodeWithScore]:
    docs, metas = get_lexical_corpus(game_id, collection)
    candidates: list[NodeWithScore] = []
    for text, meta in zip(docs, metas):
        if not text or not meta:
            continue
        if str(meta.get("faction", "")).lower() != "core":
            continue
        lower = str(text).lower()
        score = 0.0
        if "reason for adventure" in lower:
            score += 60.0
        if "card value" in lower:
            score += 35.0
        if "yearning for adventure" in lower:
            score += 15.0
        if "ace" in lower:
            score += 8.0
        if score <= 0:
            continue
        candidates.append(NodeWithScore(node=TextNode(text=str(text), metadata=meta), score=score))
    candidates.sort(key=lambda n: n.score or 0.0, reverse=True)
    return candidates[:limit]


def _brambletrek_card_score(node: NodeWithScore, question: str) -> float:
    lower_q = question.lower()
    text = node.get_content().lower()
    meta = node.metadata or {}
    faction = str(meta.get("faction", "")).lower()
    score = 0.0
    if faction == "core":
        score += 15.0
    if "reason for adventure" in text:
        score += 45.0
    if "card value" in text:
        score += 25.0
    if "reason table" in text:
        score += 20.0
    for token in ("ace", "jack", "queen", "king"):
        if token in lower_q and re.search(rf"\b{token}\b", text):
            score += 10.0
    return score


def enhance_query(question: str, brambletrek_character=None) -> str:
    return _enhance_brambletrek_query(question, brambletrek_character)


def preprocess_question(question: str, brambletrek_character=None) -> str:
    if brambletrek_character and _is_brambletrek_ending_question(question):
        if getattr(brambletrek_character, "reason_band", ""):
            from backend.games.brambletrek.characters.entity import label_for_band
            from backend.games.brambletrek.dm.curated import format_reason_ending

            reason_label = label_for_band("reasons", brambletrek_character.reason_band)
            curated = format_reason_ending(
                brambletrek_character.reason_band,
                reason_label=reason_label,
            )
            return f"{question}\n\n{curated}"
    return question


def prompt_top_k(question: str, top_k: int, brambletrek_character=None) -> int:
    return _brambletrek_prompt_top_k(question, top_k, brambletrek_character)


def result_cap(question: str, top_k: int, brambletrek_character=None) -> int:
    cap = max(top_k * 2, 16)
    if _brambletrek_tables_needed(question, brambletrek_character):
        cap = max(cap, 28)
    if _is_brambletrek_adventure_scene_prompt(question):
        cap = max(cap, 24)
    return cap


def boost_retrieval(
    nodes: list[NodeWithScore],
    *,
    game_id: str,
    question: str,
    search_q: str,
    collection,
    index,
    retrieval_k: int,
    use_hybrid: bool,
    brambletrek_character=None,
) -> list[NodeWithScore]:
    from backend.rag.retrieval_core import dedupe_nodes, retrieve_hybrid

    creation_nodes = _brambletrek_creation_table_nodes(
        game_id, collection, question, brambletrek_character
    )
    if creation_nodes:
        nodes = dedupe_nodes(creation_nodes + nodes)
    adv_id = getattr(brambletrek_character, "active_adventure", "") if brambletrek_character else ""
    if adv_id and (
        _is_brambletrek_adventure_question(question)
        or _is_brambletrek_adventure_scene_prompt(question)
        or not _brambletrek_tables_needed(question, brambletrek_character)
    ):
        adv_limit = 16 if _is_brambletrek_adventure_scene_prompt(question) else 12
        adv_nodes = _brambletrek_adventure_module_nodes(
            game_id, collection, adv_id, limit=adv_limit
        )
        if adv_nodes:
            nodes = dedupe_nodes(adv_nodes + nodes)
    elif _is_brambletrek_card_question(question):
        table_nodes = _brambletrek_reason_table_nodes(game_id, collection, limit=8)
        core_nodes = retrieve_hybrid(
            game_id=game_id,
            index=index,
            collection=collection,
            query_text=search_q,
            candidate_k=max(retrieval_k, 40),
            factions=["core"],
            use_hybrid=use_hybrid,
        )
        if core_nodes:
            ranked_core = sorted(
                dedupe_nodes(core_nodes),
                key=lambda n: (_brambletrek_card_score(n, question), n.score or 0.0),
                reverse=True,
            )
            nodes = dedupe_nodes(table_nodes + ranked_core + nodes)
    return nodes
