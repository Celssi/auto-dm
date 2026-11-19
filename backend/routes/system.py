"""Index and health API routes."""

from __future__ import annotations

import json
import queue
import threading
import time
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.config import (
    ANTHROPIC_API_KEY,
    COLLECTION_NAME,
    LANGSMITH_ENABLED,
    LANGSMITH_ENDPOINT,
    LANGSMITH_PROJECT,
)
from backend.games.registry import get_game, list_games
from backend.glossary import glossary_payload, lookup_entries
from backend.llm import resolve_claude_model
from backend.rag.engine import query_rules
from backend.rag.ingest import run_ingest
from backend.rag.recall_audit import load_recall_report, run_recall_audit, save_recall_report
from backend.rag.retrieval_core import get_collection
from backend.settings_store import load_settings, save_settings

router = APIRouter(prefix="/api", tags=["system"])
_recall_lock = threading.Lock()
_recall_cache: dict | None = None


class SettingsBody(BaseModel):
    include_faerun: bool | None = None
    use_rerank: bool | None = None


class RulesSearchBody(BaseModel):
    question: str
    include_faerun: bool = False
    game_id: str = "dnd5e"
    generate_answer: bool = True


class IngestBody(BaseModel):
    include_faerun: bool = False
    force_ocr: bool = False
    confirm_drop_faerun: bool = False
    game_id: str = "dnd5e"


def _chunk_count(game_id: str) -> int:
    collection = get_collection(game_id)
    return collection.count() if collection else 0


def _index_status() -> dict:
    counts = {game["id"]: _chunk_count(game["id"]) for game in list_games()}
    return {
        "chunk_counts": counts,
        "indexed_by_game": {gid: count > 0 for gid, count in counts.items()},
        "indexed": any(count > 0 for count in counts.values()),
    }


def _cached_recall() -> dict | None:
    global _recall_cache
    if _recall_cache:
        return _recall_cache
    loaded = load_recall_report()
    if loaded:
        _recall_cache = loaded
    return loaded


def _run_and_cache_recall() -> dict:
    global _recall_cache
    report = run_recall_audit(include_faerun=True)
    compact = save_recall_report(report)
    _recall_cache = compact
    return compact


class GlossaryLookupBody(BaseModel):
    names: list[str]
    use_rag: bool = True


@router.get("/games")
def games():
    return {"games": list_games()}


@router.get("/settings")
def get_settings():
    return {"settings": load_settings()}


@router.put("/settings")
def update_settings(body: SettingsBody):
    updates = body.model_dump(exclude_none=True)
    return {"settings": save_settings(updates)}


@router.get("/keepalive")
def keepalive():
    return {"ok": True, "ts": int(time.time())}


@router.get("/health")
def health():
    status = _index_status()
    last_recall = _cached_recall()
    return {
        "status": "ok",
        "indexed": status["indexed"],
        "indexed_by_game": status["indexed_by_game"],
        "chunk_counts": status["chunk_counts"],
        "collection": COLLECTION_NAME,
        "claude_configured": bool(ANTHROPIC_API_KEY),
        "claude_model": resolve_claude_model(),
        "langsmith_enabled": LANGSMITH_ENABLED,
        "langsmith_project": LANGSMITH_PROJECT or None,
        "langsmith_endpoint": LANGSMITH_ENDPOINT or None,
        "last_recall": last_recall,
    }


@router.get("/recall-audit")
def recall_audit_endpoint(refresh: bool = Query(False)):
    status = _index_status()
    if not status["indexed_by_game"].get("dnd5e"):
        raise HTTPException(status_code=503, detail="D&D 5e index is empty")
    with _recall_lock:
        if not refresh:
            cached = _cached_recall()
            if cached:
                return cached
        return _run_and_cache_recall()


@router.post("/index/reindex")
def reindex(body: IngestBody):
    pending: queue.Queue[tuple[str, dict] | None] = queue.Queue()

    def emit(event: str, data: dict) -> None:
        pending.put((event, data))

    def worker() -> None:
        try:
            game_id = (body.game_id or "dnd5e").strip().lower()
            known = {game["id"] for game in list_games()} | {"all"}
            if game_id not in known:
                emit("error", {"detail": f"Unknown game: {body.game_id}"})
                return

            targets = [g["id"] for g in list_games()] if game_id == "all" else [game_id]
            needs_dnd = "dnd5e" in targets
            if needs_dnd and not body.include_faerun and not body.confirm_drop_faerun:
                emit(
                    "error",
                    {
                        "detail": (
                            "Indexing D&D 5e core only would delete Faerun books from the production index. "
                            "Use Index core + Faerun, Index all books, or confirm dropping Faerun."
                        )
                    },
                )
                return

            from backend.rag.engine import clear_retrieval_caches

            ok = True
            for index, target in enumerate(targets):
                label = "D&D 5e" if target == "dnd5e" else get_game(target).label
                last = index == len(targets) - 1
                emit("progress", {"message": f"Indexing {label} books. This can take a long time."})
                if target == "dnd5e":
                    code = run_ingest(
                        core_only=not body.include_faerun,
                        include_faerun=body.include_faerun,
                        reset=True,
                        force_ocr=body.force_ocr,
                        game_id="dnd5e",
                        skip_audit=True,
                        skip_upload=not last,
                    )
                else:
                    code = run_ingest(
                        reset=True,
                        force_ocr=body.force_ocr,
                        game_id=target,
                        skip_audit=True,
                        skip_upload=not last,
                    )
                if code != 0:
                    ok = False
                    emit("progress", {"message": f"{label} indexing failed."})
                    break
            clear_retrieval_caches()
            status = _index_status()
            emit(
                "done",
                {
                    "ok": ok,
                    "chunk_count": status["chunk_counts"].get("dnd5e", 0)
                    if game_id == "dnd5e"
                    else status["chunk_counts"].get(game_id, sum(status["chunk_counts"].values())),
                    "chunk_counts": status["chunk_counts"],
                    "indexed_by_game": status["indexed_by_game"],
                },
            )
        except Exception as exc:
            emit("error", {"detail": str(exc)})
        finally:
            pending.put(None)

    def generate() -> Iterator[dict[str, str]]:
        threading.Thread(target=worker, daemon=True).start()
        while True:
            try:
                item = pending.get(timeout=15)
            except queue.Empty:
                yield {"event": "keepalive", "data": json.dumps({"ts": int(time.time())})}
                continue
            if item is None:
                break
            event, data = item
            yield {"event": event, "data": json.dumps(data)}

    return EventSourceResponse(generate())


@router.get("/glossary")
def get_glossary():
    return glossary_payload()


@router.post("/glossary/lookup")
def glossary_lookup(body: GlossaryLookupBody):
    return {"entries": lookup_entries(body.names, use_rag=body.use_rag)}


def _search_factions(game_id: str, include_faerun: bool) -> list[str]:
    plugin = get_game(game_id)
    if game_id != "dnd5e" or include_faerun:
        return plugin.get_all_factions()
    return ["player", "dm", "monsters"]


@router.post("/rules/search")
def rules_search(body: RulesSearchBody):
    factions = _search_factions(body.game_id, body.include_faerun)
    result = query_rules(
        body.question,
        game_id=body.game_id,
        factions=factions,
        use_rerank=True,
        generate_answer=body.generate_answer,
    )
    return {"answer": result.answer, "sources": result.sources}


@router.get("/debug/traces")
def debug_traces(session_id: str | None = None, limit: int = 200):
    from backend.dm.trace import read_traces

    return {
        "log_dir": "data/debug/dm",
        "events": read_traces(session_id, limit=min(limit, 500)),
    }
