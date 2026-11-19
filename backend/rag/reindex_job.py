"""Cloud Run job: rebuild D&D (core+Faerun) and Brambletrek indexes, then score recall."""

from __future__ import annotations

import json
import sys

from backend.rag.ingest import run_ingest
from backend.rag.recall_audit import run_recall_audit
from backend.rag.retrieval_core import get_collection


def _chunk_count(game_id: str) -> int:
    collection = get_collection(game_id)
    return collection.count() if collection else 0


def main() -> int:
    print("AUTO_DM_REINDEX_START", flush=True)
    dnd_code = run_ingest(
        core_only=False,
        include_faerun=True,
        reset=True,
        skip_audit=True,
        skip_upload=True,
        game_id="dnd5e",
    )
    if dnd_code != 0:
        print("AUTO_DM_REINDEX_FAIL dnd5e", flush=True)
        return dnd_code

    bt_code = run_ingest(
        reset=True,
        skip_audit=True,
        skip_upload=False,
        game_id="brambletrek",
    )
    if bt_code != 0:
        print("AUTO_DM_REINDEX_FAIL brambletrek", flush=True)
        return bt_code

    from backend.rag.engine import clear_retrieval_caches

    clear_retrieval_caches()
    counts = {"dnd5e": _chunk_count("dnd5e"), "brambletrek": _chunk_count("brambletrek")}
    print("AUTO_DM_REINDEX_COUNTS " + json.dumps(counts), flush=True)
    report = run_recall_audit(include_faerun=True)
    print(
        "AUTO_DM_REINDEX_DONE "
        + json.dumps(
            {
                "chunk_counts": counts,
                "hits": report["hits"],
                "total": report["total"],
                "recall": report["recall"],
                "misses": report["misses"],
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
