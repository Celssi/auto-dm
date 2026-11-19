"""Shared LlamaIndex document helpers for ingest."""

from __future__ import annotations

from llama_index.core import Document

EMBED_EXCLUDE_KEYS = [
    "source_file",
    "page",
    "pdf_page",
    "printed_page",
    "faction",
    "extraction",
    "page_extraction",
]
LLM_EXCLUDE_KEYS = [
    "source_file",
    "page",
    "pdf_page",
    "faction",
    "extraction",
    "page_extraction",
]


def make_rule_document(*, text: str, metadata: dict[str, str]) -> Document:
    return Document(
        text=text,
        metadata=metadata,
        excluded_embed_metadata_keys=list(EMBED_EXCLUDE_KEYS),
        excluded_llm_metadata_keys=list(LLM_EXCLUDE_KEYS),
    )
