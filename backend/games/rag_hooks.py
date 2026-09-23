"""Optional per-game RAG retrieval and ingest hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from llama_index.core.schema import NodeWithScore


@dataclass(frozen=True)
class GameRagHooks:
    """Game-specific RAG behavior; defaults are D&D-style no-ops."""

    system_prompt: Callable[[list[str] | None], str]
    ingest_hint: str = "python -m backend.rag.ingest --core"
    run_ingest: Callable[..., int] | None = None
    enhance_query: Callable[[str, dict[str, Any] | None], str] | None = None
    adjust_top_k: Callable[[str, int, dict[str, Any] | None], int] | None = None
    boost_retrieval: Callable[..., list[NodeWithScore]] | None = None
    result_cap: Callable[[str, int, dict[str, Any] | None], int] | None = None
