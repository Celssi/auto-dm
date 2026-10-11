"""Game-scoped rulebook catalog for the in-app PDF reader."""

from __future__ import annotations

from pathlib import Path

from backend.games.registry import get_game
from backend.gcs_sync import pdf_available

# Add to the printed page to get the 1-based PDF page. CDE: printed N is PDF index N-2.
PAGE_OFFSETS: dict[str, int] = {
    "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf": -1,
}

EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "dnd5e/player.pdf": ("phb", "player's handbook", "players handbook"),
    "dnd5e/dm.pdf": ("dmg", "dungeon master's guide", "dungeon masters guide"),
    "dnd5e/monsters.pdf": ("mm", "monster manual"),
    "dnd5e/heroes_faerun.pdf": ("heroes of faerun", "heroes of faerûn"),
    "dnd5e/adventures_faerun.pdf": ("adventures in faerun", "adventures in faerûn"),
    "brambletrek/Brambletrek_-_Complete_Digital_Edition.pdf": (
        "complete digital edition",
        "cde",
        "brambletrek core",
    ),
    "brambletrek/Brambletrek_-_A_Birthday_of_Wonders.pdf": ("birthday of wonders",),
    "brambletrek/Brambletrek_-_Winter_Gift.pdf": ("winter gift",),
}


def _aliases(book_id: str, label: str) -> list[str]:
    names = {label.strip().lower(), Path(book_id).stem.lower().replace("_", " ").replace("-", " ")}
    names.update(EXTRA_ALIASES.get(book_id, ()))
    return sorted(name for name in names if name)


def list_books(game_id: str) -> list[dict[str, object]]:
    game = get_game(game_id)
    books: list[dict[str, object]] = []
    for book_id, meta in game.pdf_sources.items():
        if not pdf_available(book_id):
            continue
        label = str(meta.get("label") or book_id)
        books.append(
            {
                "id": book_id,
                "label": label,
                "faction": str(meta.get("faction") or ""),
                "page_offset": PAGE_OFFSETS.get(book_id, 0),
                "aliases": _aliases(book_id, label),
            }
        )
    return books


def resolve_book(game_id: str, book_id: str) -> dict[str, object] | None:
    for book in list_books(game_id):
        if book["id"] == book_id:
            return book
    return None


def match_source_label(game_id: str, source_label: str) -> dict[str, object] | None:
    needle = source_label.strip().lower()
    if not needle:
        return None
    for book in list_books(game_id):
        aliases = book.get("aliases")
        if isinstance(aliases, list) and needle in aliases:
            return book
        label = str(book.get("label") or "").lower()
        if needle == label or needle in label:
            return book
    return None
