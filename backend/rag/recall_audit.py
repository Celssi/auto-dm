"""Score D&D 5e retrieval against the Saruman audit query set."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUERIES_PATH = Path(__file__).resolve().parent / "saruman_queries.json"


def load_audit_queries(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or QUERIES_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def score_sources(sources: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    """Hit if the expected title or every expected term appears in retrieved text."""
    blob_parts: list[str] = []
    pages: list[str] = []
    for source in sources:
        blob_parts.append(str(source.get("section_title") or ""))
        blob_parts.append(str(source.get("source_label") or ""))
        blob_parts.append(str(source.get("text") or ""))
        pages.append(str(source.get("printed_page") or source.get("page") or ""))
    blob = " ".join(blob_parts).lower()
    title = str(spec.get("expect_title") or "").strip().lower()
    terms = [str(term).lower() for term in (spec.get("expect_terms") or [])]
    title_hit = bool(title) and title in blob
    terms_hit = bool(terms) and all(term in blob for term in terms)
    want_page = str(spec.get("printed_page") or "").strip()
    page_hit = bool(want_page) and want_page in pages
    return {
        "id": spec.get("id"),
        "hit": title_hit or terms_hit,
        "title_hit": title_hit,
        "terms_hit": terms_hit,
        "page_hit": page_hit,
        "printed_page": want_page,
        "top_sections": [str(source.get("section_title") or "") for source in sources[:3]],
        "top_pages": pages[:3],
    }


def run_recall_audit(
    *,
    game_id: str = "dnd5e",
    include_faerun: bool = True,
    top_k: int = 8,
    use_rerank: bool = True,
    queries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from backend.games.registry import get_game
    from backend.rag.engine import clear_retrieval_caches, retrieve_nodes
    from backend.rag.retrieval_core import get_collection, nodes_to_sources

    clear_retrieval_caches()
    plugin = get_game(game_id)
    if game_id != "dnd5e" or include_faerun:
        factions = plugin.get_all_factions()
    else:
        factions = ["player", "dm", "monsters"]
    collection = get_collection(game_id)
    chunk_count = collection.count() if collection else 0
    specs = queries if queries is not None else load_audit_queries()
    results: list[dict[str, Any]] = []
    for spec in specs:
        nodes = retrieve_nodes(
            str(spec["query"]),
            game_id=game_id,
            top_k=top_k,
            factions=factions,
            use_rerank=use_rerank,
        )
        scored = score_sources(nodes_to_sources(nodes), spec)
        scored["query"] = spec["query"]
        results.append(scored)
    hits = sum(1 for row in results if row["hit"])
    page_hits = sum(1 for row in results if row["page_hit"])
    total = len(results)
    report = {
        "game_id": game_id,
        "chunk_count": chunk_count,
        "hits": hits,
        "page_hits": page_hits,
        "total": total,
        "recall": round(hits / total, 4) if total else 0.0,
        "page_recall": round(page_hits / total, 4) if total else 0.0,
        "misses": [row["id"] for row in results if not row["hit"]],
        "page_misses": [row["id"] for row in results if not row["page_hit"]],
        "results": results,
    }
    print(f"RECALL {hits}/{total} ({report['recall']:.0%}) page {page_hits}/{total}")
    for row in results:
        flag = "HIT" if row["hit"] else "MISS"
        page_flag = "p+" if row["page_hit"] else "p-"
        print(f"  {flag} {page_flag} {row['id']}: {row['query']}")
    print("AUTO_DM_RECALL_JSON:" + json.dumps(report, ensure_ascii=True))
    return report


def main() -> None:
    run_recall_audit()


if __name__ == "__main__":
    main()
