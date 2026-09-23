"""RAG query engine for game rules."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from llama_index.core.schema import NodeWithScore

from backend.config import TOP_K_DEFAULT
from backend.games.registry import DEFAULT_GAME_ID, get_game
from backend.llm import ChatProvider, get_llamaindex_chat_llm
from backend.rag.retrieval_core import (
    build_index,
    dedupe_nodes,
    get_collection,
    nodes_to_sources,
    rerank_nodes,
    retrieve_hybrid,
)


@dataclass
class RagResult:
    answer: str
    sources: list[dict]


def _format_context(nodes: list[NodeWithScore]) -> str:
    parts: list[str] = []
    for i, nws in enumerate(nodes, 1):
        meta = nws.node.metadata or {}
        label = meta.get("source_label", meta.get("source_file", "Unknown"))
        page = meta.get("page", "?")
        section = meta.get("section_title", "")
        header = f"[{i}] {label} p.{page}"
        if section:
            header += f" — {section}"
        parts.append(f"{header}\n{nws.node.get_content()}")
    return "\n\n---\n\n".join(parts)


def _character_by_id(char_id: str) -> dict[str, Any] | None:
    if not char_id:
        return None
    from backend.storage import get_character

    return get_character(char_id)


def retrieve_nodes(
    question: str,
    *,
    game_id: str = DEFAULT_GAME_ID,
    top_k: int = TOP_K_DEFAULT,
    factions: list[str] | None = None,
    candidate_k: int | None = None,
    use_hybrid: bool = True,
    use_rerank: bool = False,
    character: dict[str, Any] | None = None,
) -> list[NodeWithScore]:
    plugin = get_game(game_id)
    hooks = plugin.rag
    search_q = question
    if hooks.enhance_query:
        search_q = hooks.enhance_query(question, character)
    if hooks.adjust_top_k:
        top_k = hooks.adjust_top_k(question, top_k, character)

    char_id = str((character or {}).get("id") or "")
    key = hashlib.sha256(
        f"{game_id}|{search_q}|{top_k}|{sorted(factions or [])}|{use_rerank}|{char_id}".encode()
    ).hexdigest()
    return list(
        _retrieve_nodes_cached(
            key,
            search_q,
            game_id,
            top_k,
            tuple(factions or ()),
            candidate_k,
            use_hybrid,
            use_rerank,
            char_id,
        )
    )


@lru_cache(maxsize=256)
def _retrieve_nodes_cached(
    _key: str,
    question: str,
    game_id: str,
    top_k: int,
    factions: tuple[str, ...],
    candidate_k: int | None,
    use_hybrid: bool,
    use_rerank: bool,
    _char_items: str,
) -> tuple[NodeWithScore, ...]:
    plugin = get_game(game_id)
    hooks = plugin.rag
    faction_list = list(factions) if factions else None
    collection = get_collection(game_id)
    if collection is None:
        return ()
    index = build_index(collection)
    pool = candidate_k or max(top_k * 4, 12)
    character = _character_by_id(_char_items) if _char_items else None
    nodes = retrieve_hybrid(
        game_id=game_id,
        index=index,
        collection=collection,
        query_text=question,
        candidate_k=pool,
        factions=faction_list,
        use_hybrid=use_hybrid,
    )
    nodes = dedupe_nodes(nodes)
    if hooks.boost_retrieval:
        nodes = hooks.boost_retrieval(
            nodes,
            game_id=game_id,
            question=question,
            search_q=question,
            collection=collection,
            index=index,
            retrieval_k=pool,
            use_hybrid=use_hybrid,
            character=character,
        )
    if use_rerank and nodes:
        nodes = rerank_nodes(question, nodes, use_rerank=True)
    cap = top_k
    if hooks.result_cap:
        cap = hooks.result_cap(question, top_k, character)
    return tuple(nodes[:cap])


def query_rules(
    question: str,
    *,
    game_id: str = DEFAULT_GAME_ID,
    top_k: int = TOP_K_DEFAULT,
    factions: list[str] | None = None,
    use_rerank: bool = True,
    chat_provider: ChatProvider = "claude",
    generate_answer: bool = True,
    character: dict[str, Any] | None = None,
) -> RagResult:
    plugin = get_game(game_id)
    nodes = retrieve_nodes(
        question,
        game_id=game_id,
        top_k=top_k,
        factions=factions,
        use_rerank=use_rerank,
        character=character,
    )
    sources = nodes_to_sources(nodes)
    ingest_hint = plugin.rag.ingest_hint
    if not generate_answer or not nodes:
        if not nodes:
            return RagResult(
                answer=f"No indexed rules found. Run `{ingest_hint}` first.",
                sources=[],
            )
        return RagResult(answer="", sources=sources)

    context = _format_context(nodes)
    system = plugin.rag.system_prompt(factions)
    llm = get_llamaindex_chat_llm(chat_provider)
    prompt = f"{system}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    response = llm.complete(prompt)
    answer = str(response).strip()
    return RagResult(answer=answer, sources=sources)
