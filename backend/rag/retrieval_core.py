"""Shared retrieval utilities (hybrid search, Chroma access)."""

from __future__ import annotations

import math
import re
from functools import lru_cache

import chromadb
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores import FilterCondition, MetadataFilters
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

from backend.config import (
    CHAT_MODEL,
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBED_DOCUMENT_PREFIX,
    EMBED_MODEL,
    EMBED_QUERY_PREFIX,
    OLLAMA_BASE_URL,
    OLLAMA_REQUEST_TIMEOUT,
    RERANK_MODEL,
)

_LEXICAL_CACHE: dict[str, tuple[list[str], list[dict]]] = {}
_settings_initialized = False


@lru_cache(maxsize=1)
def _get_chroma_client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection(game_id: str = "dnd5e"):
    _ = game_id
    if not CHROMA_DIR.exists():
        return None
    client = _get_chroma_client()
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return None
    if collection.count() == 0:
        return None
    return collection


def _ensure_settings():
    global _settings_initialized
    if _settings_initialized:
        return
    Settings.embed_model = OllamaEmbedding(
        model_name=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
        text_instruction=EMBED_DOCUMENT_PREFIX,
        query_instruction=EMBED_QUERY_PREFIX,
    )
    Settings.llm = Ollama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        request_timeout=OLLAMA_REQUEST_TIMEOUT,
    )
    _settings_initialized = True


def build_index(collection) -> VectorStoreIndex:
    _ensure_settings()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreIndex.from_vector_store(vector_store)


def faction_filters(factions: list[str] | None) -> MetadataFilters | None:
    if not factions:
        return None
    from llama_index.core.vector_stores import ExactMatchFilter

    filters = [ExactMatchFilter(key="faction", value=f) for f in factions]
    return MetadataFilters(filters=filters, condition=FilterCondition.OR)


def nodes_to_sources(nodes: list[NodeWithScore]) -> list[dict]:
    sources: list[dict] = []
    for n in nodes:
        meta = n.metadata or {}
        sources.append(
            {
                "text": n.get_content(),
                "source_file": meta.get("source_file", ""),
                "source_label": meta.get("source_label", ""),
                "page": meta.get("page", ""),
                "faction": meta.get("faction", ""),
                "section_title": meta.get("section_title", ""),
                "score": round(n.score, 4) if n.score is not None else None,
            }
        )
    return sources


def dedupe_nodes(nodes: list[NodeWithScore]) -> list[NodeWithScore]:
    seen: set[tuple[str, str, str]] = set()
    out: list[NodeWithScore] = []
    for n in nodes:
        meta = n.metadata or {}
        key = (
            str(meta.get("source_file", "")),
            str(meta.get("page", "")),
            n.get_content()[:120],
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def _node_key(node: NodeWithScore) -> tuple[str, str, str]:
    meta = node.metadata or {}
    return (
        str(meta.get("source_file", "")),
        str(meta.get("page", "")),
        node.get_content()[:120],
    )


def _retrieve_dense(
    index: VectorStoreIndex,
    query_text: str,
    limit: int,
    factions: list[str] | None,
) -> list[NodeWithScore]:
    retriever = index.as_retriever(
        similarity_top_k=limit,
        filters=faction_filters(factions),
    )
    return retriever.retrieve(query_text)


def _doc_matches_factions(meta: dict | None, factions: list[str] | None) -> bool:
    if not factions:
        return True
    if not meta:
        return False
    return str(meta.get("faction", "")) in factions


_SYNONYM_MAP: dict[str, list[str]] = {
    "hp": ["hit points", "health"],
    "ac": ["armor class", "armour class"],
    "dc": ["difficulty class"],
    "xp": ["experience points"],
    "pb": ["proficiency bonus"],
    "str": ["strength"],
    "dex": ["dexterity"],
    "con": ["constitution"],
    "int": ["intelligence"],
    "wis": ["wisdom"],
    "cha": ["charisma"],
    "cr": ["challenge rating"],
    "gp": ["gold pieces", "gold"],
    "sp": ["silver pieces"],
    "cp": ["copper pieces"],
    "aoo": ["opportunity attack", "attack of opportunity"],
    "conc": ["concentration"],
}


def expand_query(question: str) -> str:
    lower = question.lower()
    extras: list[str] = []
    for abbr, expansions in _SYNONYM_MAP.items():
        pattern = rf"\b{re.escape(abbr)}\b"
        if re.search(pattern, lower):
            extras.extend(expansions)
    if extras:
        return f"{question} {' '.join(extras)}"
    return question


class _BM25Corpus:
    """Precomputed BM25 statistics for a document corpus."""

    def __init__(self, docs: list[str], metas: list[dict], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.metas = metas
        self.k1 = k1
        self.b = b
        self.doc_tokens: list[list[str]] = []
        self.doc_freqs: dict[str, int] = {}
        total_len = 0
        for text in docs:
            tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", (text or "").lower())
            self.doc_tokens.append(tokens)
            total_len += len(tokens)
            seen: set[str] = set()
            for t in tokens:
                if t not in seen:
                    self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1
                    seen.add(t)
        self.n = len(docs)
        self.avgdl = total_len / max(1, self.n)

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        tokens = self.doc_tokens[doc_idx]
        dl = len(tokens)
        freq_map: dict[str, int] = {}
        for t in tokens:
            freq_map[t] = freq_map.get(t, 0) + 1
        s = 0.0
        for qt in query_tokens:
            tf = freq_map.get(qt, 0)
            if tf == 0:
                continue
            df = self.doc_freqs.get(qt, 0)
            idf = math.log((self.n - df + 0.5) / (df + 0.5) + 1.0)
            tf_norm = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            )
            s += idf * tf_norm
        return s


_BM25_CACHE: dict[str, _BM25Corpus] = {}


def get_lexical_corpus(game_id: str, collection) -> tuple[list[str], list[dict]]:
    cached = _LEXICAL_CACHE.get(game_id)
    if cached is not None:
        return cached
    raw = collection.get(include=["documents", "metadatas"])
    docs = raw.get("documents") or []
    metas = raw.get("metadatas") or []
    _LEXICAL_CACHE[game_id] = (docs, metas)
    return docs, metas


def _get_bm25(game_id: str, collection) -> _BM25Corpus:
    if game_id in _BM25_CACHE:
        return _BM25_CACHE[game_id]
    docs, metas = get_lexical_corpus(game_id, collection)
    corpus = _BM25Corpus(docs, metas)
    _BM25_CACHE[game_id] = corpus
    return corpus


def _lexical_retrieve(
    game_id: str,
    collection,
    query_text: str,
    limit: int,
    factions: list[str] | None,
) -> list[NodeWithScore]:
    corpus = _get_bm25(game_id, collection)
    expanded = expand_query(query_text)
    q_tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", expanded.lower())
    phrase = query_text.strip().lower()

    scored: list[tuple[float, int]] = []
    for i in range(corpus.n):
        if not corpus.docs[i]:
            continue
        if not _doc_matches_factions(corpus.metas[i], factions):
            continue
        s = corpus.score(q_tokens, i)
        if phrase and phrase in corpus.docs[i].lower():
            s += 10.0
        if s > 0:
            scored.append((s, i))

    scored.sort(key=lambda x: x[0], reverse=True)
    nodes: list[NodeWithScore] = []
    for s, i in scored[:limit]:
        node = TextNode(text=corpus.docs[i], metadata=corpus.metas[i] or {})
        nodes.append(NodeWithScore(node=node, score=float(s)))
    return nodes


def _fuse_nodes_rrf(
    dense_nodes: list[NodeWithScore],
    lexical_nodes: list[NodeWithScore],
    limit: int,
) -> list[NodeWithScore]:
    combined: dict[tuple[str, str, str], tuple[float, NodeWithScore]] = {}
    k = 60.0
    for rank, node in enumerate(dense_nodes, 1):
        key = _node_key(node)
        score = 1.0 / (k + rank)
        prev = combined.get(key)
        if prev is None:
            combined[key] = (score, node)
        else:
            combined[key] = (prev[0] + score, prev[1])
    for rank, node in enumerate(lexical_nodes, 1):
        key = _node_key(node)
        score = 1.0 / (k + rank)
        prev = combined.get(key)
        if prev is None:
            combined[key] = (score, node)
        else:
            combined[key] = (prev[0] + score, prev[1])

    ranked = sorted(combined.values(), key=lambda x: x[0], reverse=True)
    fused: list[NodeWithScore] = []
    for score, node in ranked[:limit]:
        node.score = round(score, 6)
        fused.append(node)
    return fused


def retrieve_hybrid(
    game_id: str,
    index: VectorStoreIndex,
    collection,
    query_text: str,
    candidate_k: int,
    factions: list[str] | None,
    use_hybrid: bool = True,
) -> list[NodeWithScore]:
    dense = _retrieve_dense(index, query_text, candidate_k, factions)
    if not use_hybrid:
        return dedupe_nodes(dense)
    lexical = _lexical_retrieve(game_id, collection, query_text, candidate_k, factions)
    return dedupe_nodes(_fuse_nodes_rrf(dense, lexical, candidate_k))


_reranker = None
_reranker_unavailable: str | None = None


def rerank_available() -> bool:
    """True if sentence-transformers cross-encoder can be loaded."""
    global _reranker_unavailable
    if _reranker_unavailable is not None:
        return _reranker_unavailable == ""
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
    except ImportError:
        _reranker_unavailable = "sentence-transformers not installed"
        return False
    _reranker_unavailable = ""
    return True


def rerank_unavailable_reason() -> str | None:
    rerank_available()
    return _reranker_unavailable or None


def _get_reranker():
    global _reranker, _reranker_unavailable
    if _reranker is not None:
        return _reranker
    try:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder(RERANK_MODEL)
        _reranker_unavailable = ""
        return _reranker
    except ImportError as exc:
        _reranker_unavailable = str(exc)
        raise


def rerank_nodes(
    query: str,
    nodes: list[NodeWithScore],
    *,
    use_rerank: bool = True,
) -> list[NodeWithScore]:
    """Reorder hybrid candidates with a cross-encoder (game-agnostic second stage)."""
    if not use_rerank or len(nodes) <= 1:
        return nodes
    if not rerank_available():
        return nodes
    try:
        model = _get_reranker()
    except ImportError:
        return nodes

    pairs = [(query, node.get_content()) for node in nodes]
    raw_scores = model.predict(pairs)
    scored: list[tuple[float, NodeWithScore]] = []
    for idx, node in enumerate(nodes):
        score = float(raw_scores[idx])
        node.score = round(score, 6)
        scored.append((score, node))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [node for _, node in scored]
