"""RAG query engine for D&D 5e rules."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache

from llama_index.core.schema import NodeWithScore

from backend.config import TOP_K_DEFAULT
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


def _build_system_prompt(factions: list[str] | None) -> str:
    scope = ", ".join(factions) if factions else "Player's Handbook, DMG, Monster Manual"
    return f"""You are a D&D 5e (2024) rules assistant for solo play.
Answer using ONLY the provided rule excerpts from: {scope}.
Cite sources as [Book p.X]. If unsure, say so.
Keep answers concise and actionable for a solo player."""


def retrieve_nodes(
    question: str,
    *,
    top_k: int = TOP_K_DEFAULT,
    factions: list[str] | None = None,
    candidate_k: int | None = None,
    use_hybrid: bool = True,
    use_rerank: bool = False,
) -> list[NodeWithScore]:
    key = hashlib.sha256(
        f"{question}|{top_k}|{sorted(factions or [])}|{use_rerank}".encode()
    ).hexdigest()
    return list(
        _retrieve_nodes_cached(
            key, question, top_k, tuple(factions or ()), candidate_k, use_hybrid, use_rerank
        )
    )


@lru_cache(maxsize=256)
def _retrieve_nodes_cached(
    _key: str,
    question: str,
    top_k: int,
    factions: tuple[str, ...],
    candidate_k: int | None,
    use_hybrid: bool,
    use_rerank: bool,
) -> tuple[NodeWithScore, ...]:
    faction_list = list(factions) if factions else None
    collection = get_collection()
    if collection is None:
        return ()
    index = build_index(collection)
    pool = candidate_k or max(top_k * 4, 12)
    nodes = retrieve_hybrid(
        game_id="dnd5e",
        index=index,
        collection=collection,
        query_text=question,
        candidate_k=pool,
        factions=faction_list,
        use_hybrid=use_hybrid,
    )
    nodes = dedupe_nodes(nodes)
    if use_rerank and nodes:
        nodes = rerank_nodes(question, nodes, use_rerank=True)
    return tuple(nodes[:top_k])


def query_rules(
    question: str,
    *,
    top_k: int = TOP_K_DEFAULT,
    factions: list[str] | None = None,
    use_rerank: bool = True,
    chat_provider: ChatProvider = "claude",
    generate_answer: bool = True,
) -> RagResult:
    nodes = retrieve_nodes(
        question,
        top_k=top_k,
        factions=factions,
        use_rerank=use_rerank,
    )
    sources = nodes_to_sources(nodes)
    if not generate_answer or not nodes:
        if not nodes:
            return RagResult(
                answer="No indexed rules found. Run `python -m scripts.ingest --core` first.",
                sources=[],
            )
        return RagResult(answer="", sources=sources)

    context = _format_context(nodes)
    system = _build_system_prompt(factions)
    llm = get_llamaindex_chat_llm(chat_provider)
    prompt = f"{system}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    response = llm.complete(prompt)
    answer = str(response).strip()
    return RagResult(answer=answer, sources=sources)
