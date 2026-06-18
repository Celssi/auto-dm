"""Index and health API routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.config import ANTHROPIC_API_KEY, CLAUDE_CHAT_MODEL, COLLECTION_NAME
from backend.rag.ingest import run_ingest
from backend.rag.retrieval_core import get_collection
from backend.rag.engine import query_rules
from backend.rag.plugin import get_all_factions
from backend.glossary import glossary_payload, lookup_entries
from backend.settings_store import load_settings, save_settings
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["system"])


class SettingsBody(BaseModel):
    include_faerun: bool | None = None
    use_rerank: bool | None = None


class RulesSearchBody(BaseModel):
    question: str
    include_faerun: bool = False


class IngestBody(BaseModel):
    include_faerun: bool = False
    force_ocr: bool = False


class GlossaryLookupBody(BaseModel):
    names: list[str]
    use_rag: bool = True


@router.get("/settings")
def get_settings():
    return {"settings": load_settings()}


@router.put("/settings")
def update_settings(body: SettingsBody):
    updates = body.model_dump(exclude_none=True)
    return {"settings": save_settings(updates)}


@router.get("/health")
def health():
    collection = get_collection()
    indexed = collection is not None and collection.count() > 0
    return {
        "status": "ok",
        "indexed": indexed,
        "collection": COLLECTION_NAME,
        "claude_configured": bool(ANTHROPIC_API_KEY),
        "claude_model": CLAUDE_CHAT_MODEL,
    }


@router.post("/index/reindex")
def reindex(body: IngestBody):
    code = run_ingest(
        core_only=not body.include_faerun,
        include_faerun=body.include_faerun,
        reset=True,
        force_ocr=body.force_ocr,
    )
    collection = get_collection()
    count = collection.count() if collection else 0
    return {"ok": code == 0, "chunk_count": count}


@router.get("/glossary")
def get_glossary():
    return glossary_payload()


@router.post("/glossary/lookup")
def glossary_lookup(body: GlossaryLookupBody):
    return {"entries": lookup_entries(body.names, use_rag=body.use_rag)}


@router.post("/rules/search")
def rules_search(body: RulesSearchBody):
    factions = get_all_factions() if body.include_faerun else ["player", "dm", "monsters"]
    result = query_rules(body.question, factions=factions, use_rerank=True)
    return {"answer": result.answer, "sources": result.sources}


@router.get("/debug/traces")
def debug_traces(session_id: str | None = None, limit: int = 200):
    from backend.dm.trace import read_traces

    return {
        "log_dir": "data/debug/dm",
        "events": read_traces(session_id, limit=min(limit, 500)),
    }
