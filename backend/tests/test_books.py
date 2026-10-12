from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.book_catalog import list_books
from backend.book_store import load_book_state, save_book_state
from backend.routes.books import router


def test_list_books_hides_missing_files(monkeypatch):
    monkeypatch.setattr("backend.book_catalog.pdf_available", lambda key: key == "dnd5e/player.pdf")
    books = list_books("dnd5e")
    ids = [book["id"] for book in books]
    assert ids == ["dnd5e/player.pdf"]
    assert books[0]["label"] == "Player's Handbook (2024)"


def test_bookmark_round_trip(monkeypatch, tmp_path):
    path = tmp_path / "books.json"
    monkeypatch.setattr("backend.book_store.BOOKS_PATH", path)
    monkeypatch.setattr("backend.persist.after_write", lambda _path: None)

    saved = save_book_state(
        {
            "bookmarks": [{"book_id": "dnd5e/player.pdf", "page": 12, "label": "Stealth"}],
            "lastByGame": {"dnd5e": {"book_id": "dnd5e/player.pdf", "page": 12}},
        }
    )
    assert saved["bookmarks"][0]["page"] == 12
    assert saved["bookmarks"][0]["id"]
    assert saved["lastByGame"]["dnd5e"]["book_id"] == "dnd5e/player.pdf"
    assert load_book_state()["bookmarks"][0]["label"] == "Stealth"


def _gcs_book_app(monkeypatch):
    monkeypatch.setattr(
        "backend.routes.books.resolve_book",
        lambda _game, book_id: {"id": book_id},
    )
    monkeypatch.setattr(
        "backend.routes.books.local_pdf_path",
        lambda _key: Path("/missing/player.pdf"),
    )
    monkeypatch.setattr("backend.routes.books.pdf_byte_size", lambda _key: 100)
    monkeypatch.setattr(
        "backend.routes.books.read_pdf_bytes",
        lambda _key, start=0, end=None: b"x" * ((end if end is not None else 99) - start + 1),
    )
    monkeypatch.setattr("backend.routes.books.is_local_dev_bypass", lambda _request: False)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_range_request_returns_206(monkeypatch):
    from backend.routes.books import issue_file_ticket

    client = _gcs_book_app(monkeypatch)
    ticket = issue_file_ticket("dnd5e/player.pdf")
    res = client.get(
        f"/api/books/dnd5e/player.pdf/file?game_id=dnd5e&ticket={ticket}",
        headers={"Range": "bytes=0-9"},
    )

    assert res.status_code == 206
    assert res.content == b"xxxxxxxxxx"
    assert res.headers["content-range"] == "bytes 0-9/100"
    assert res.headers["accept-ranges"] == "bytes"


def test_file_requires_ticket(monkeypatch):
    client = _gcs_book_app(monkeypatch)
    res = client.get("/api/books/dnd5e/player.pdf/file?game_id=dnd5e")
    assert res.status_code == 401


def test_head_returns_pdf_size(monkeypatch):
    from backend.routes.books import issue_file_ticket

    client = _gcs_book_app(monkeypatch)
    ticket = issue_file_ticket("dnd5e/player.pdf")
    res = client.head(f"/api/books/dnd5e/player.pdf/file?game_id=dnd5e&ticket={ticket}")
    assert res.status_code == 200
    assert res.headers["content-length"] == "100"
    assert res.headers["accept-ranges"] == "bytes"


def test_expired_ticket_is_rejected(monkeypatch):
    from backend.routes.books import issue_file_ticket

    client = _gcs_book_app(monkeypatch)
    ticket = issue_file_ticket("dnd5e/player.pdf", ttl=-10)
    res = client.get(f"/api/books/dnd5e/player.pdf/file?game_id=dnd5e&ticket={ticket}")
    assert res.status_code == 401


def test_unranged_large_file_returns_first_chunk(monkeypatch):
    from backend.routes.books import issue_file_ticket

    client = _gcs_book_app(monkeypatch)
    monkeypatch.setattr("backend.routes.books.pdf_byte_size", lambda _key: 200_000)
    monkeypatch.setattr(
        "backend.routes.books.read_pdf_bytes",
        lambda _key, start=0, end=None: b"x" * ((end if end is not None else 199_999) - start + 1),
    )
    ticket = issue_file_ticket("dnd5e/player.pdf")
    res = client.get(f"/api/books/dnd5e/player.pdf/file?game_id=dnd5e&ticket={ticket}")
    assert res.status_code == 206
    assert len(res.content) == 64 * 1024
    assert res.headers["content-range"] == "bytes 0-65535/200000"
