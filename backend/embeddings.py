"""In-process nomic embeddings for ingest and retrieval."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.core.embeddings import BaseEmbedding

from backend.config import EMBED_DOCUMENT_PREFIX, EMBED_HF_MODEL, EMBED_QUERY_PREFIX


class NomicEmbedding(BaseEmbedding):
    _model: Any = PrivateAttr()

    def __init__(self, model_name: str = EMBED_HF_MODEL, **kwargs: Any) -> None:
        super().__init__(model_name=model_name, **kwargs)
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, trust_remote_code=True)

    def _encode(self, text: str, prefix: str) -> list[float]:
        payload = text if text.startswith(prefix) else f"{prefix}{text}"
        vector = self._model.encode(payload, normalize_embeddings=True)
        return vector.tolist()

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._encode(query, EMBED_QUERY_PREFIX)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._encode(text, EMBED_DOCUMENT_PREFIX)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        payloads = [
            text if text.startswith(EMBED_DOCUMENT_PREFIX) else f"{EMBED_DOCUMENT_PREFIX}{text}"
            for text in texts
        ]
        vectors = self._model.encode(payloads, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._get_text_embedding(text)


@lru_cache(maxsize=1)
def build_embed_model() -> BaseEmbedding:
    return NomicEmbedding()
