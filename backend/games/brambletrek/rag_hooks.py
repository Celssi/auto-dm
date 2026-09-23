"""Brambletrek RAG hooks."""

from __future__ import annotations

from typing import Any

from llama_index.core.schema import NodeWithScore

from backend.games.rag_hooks import GameRagHooks


def _brambletrek_system_prompt(factions: list[str] | None) -> str:
    scope = ", ".join(factions) if factions else "Brambletrek core rules and adventures"
    return f"""You are a Brambletrek rules assistant for solo journaling play.
Answer using ONLY the provided rule excerpts from: {scope}.
Cite sources with file name and page number. If unsure, say so.
Keep answers concise and practical for a game facilitator."""


def _char_entity(character: dict[str, Any] | None):
    if not character:
        return None
    from backend.games.brambletrek.characters.entity import character_from_dict

    return character_from_dict(character)


def _enhance_query(question: str, character: dict[str, Any] | None) -> str:
    from backend.games.brambletrek.retrieval import enhance_query

    return enhance_query(question, _char_entity(character))


def _adjust_top_k(question: str, top_k: int, character: dict[str, Any] | None) -> int:
    from backend.games.brambletrek.retrieval import prompt_top_k

    return prompt_top_k(question, top_k, _char_entity(character))


def _boost_retrieval(
    nodes: list[NodeWithScore],
    *,
    game_id: str,
    question: str,
    search_q: str,
    collection,
    index,
    retrieval_k: int,
    use_hybrid: bool,
    character: dict[str, Any] | None,
) -> list[NodeWithScore]:
    from backend.games.brambletrek.retrieval import boost_retrieval

    return boost_retrieval(
        nodes,
        game_id=game_id,
        question=question,
        search_q=search_q,
        collection=collection,
        index=index,
        retrieval_k=retrieval_k,
        use_hybrid=use_hybrid,
        brambletrek_character=_char_entity(character),
    )


def _result_cap(question: str, top_k: int, character: dict[str, Any] | None) -> int:
    from backend.games.brambletrek.retrieval import result_cap

    return result_cap(question, top_k, _char_entity(character))


def _run_brambletrek_ingest(
    *,
    core_only: bool = True,
    include_faerun: bool = False,
    reset: bool = True,
    use_ocr: bool = True,
    force_ocr: bool = False,
    game_id: str = "brambletrek",
    skip_audit: bool = False,
) -> int:
    from backend.rag.ingest import run_brambletrek_ingest

    _ = (core_only, include_faerun, game_id)
    return run_brambletrek_ingest(
        reset=reset,
        use_ocr=use_ocr,
        force_ocr=force_ocr,
        skip_audit=skip_audit,
    )


BRAMBLETREK_RAG_HOOKS = GameRagHooks(
    system_prompt=_brambletrek_system_prompt,
    ingest_hint="python -m backend.rag.ingest --game brambletrek",
    run_ingest=_run_brambletrek_ingest,
    enhance_query=_enhance_query,
    adjust_top_k=_adjust_top_k,
    boost_retrieval=_boost_retrieval,
    result_cap=_result_cap,
)
