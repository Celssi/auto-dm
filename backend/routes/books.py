"""In-app rulebook PDF API."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from backend.book_catalog import list_books, resolve_book
from backend.book_store import load_book_state, save_book_state
from backend.config import local_pdf_path
from backend.gcs_sync import pdf_byte_size, read_pdf_bytes

router = APIRouter(prefix="/api/books", tags=["books"])

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


class BookmarkBody(BaseModel):
    id: str | None = None
    book_id: str
    page: int = Field(ge=1)
    label: str | None = None
    created_at: str | None = None


class LastReadBody(BaseModel):
    book_id: str
    page: int = Field(ge=1)


class BookStateBody(BaseModel):
    bookmarks: list[BookmarkBody] | None = None
    lastByGame: dict[str, LastReadBody] | None = None


@router.get("")
def books(game_id: str = Query(default="dnd5e")):
    return {"books": list_books(game_id)}


@router.get("/state")
def get_state():
    return load_book_state()


@router.put("/state")
def put_state(body: BookStateBody):
    updates: dict[str, Any] = {}
    if body.bookmarks is not None:
        updates["bookmarks"] = [item.model_dump() for item in body.bookmarks]
    if body.lastByGame is not None:
        updates["lastByGame"] = {game_id: item.model_dump() for game_id, item in body.lastByGame.items()}
    return save_book_state(updates)


@router.get("/{book_id:path}/file")
def book_file(book_id: str, request: Request, game_id: str = Query(default="dnd5e")):
    book = resolve_book(game_id, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    local = local_pdf_path(book_id)
    if local.is_file():
        return FileResponse(
            local,
            media_type="application/pdf",
            filename=local.name,
            headers={"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=60"},
        )

    size = pdf_byte_size(book_id)
    if size is None or size <= 0:
        raise HTTPException(status_code=404, detail="Book file not available")

    parsed = _parse_range(request.headers.get("range"), size)
    if parsed is None:
        data = read_pdf_bytes(book_id)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(data)),
                "Cache-Control": "private, max-age=60",
            },
        )

    start, end = parsed
    data = read_pdf_bytes(book_id, start=start, end=end)
    return Response(
        content=data,
        status_code=206,
        media_type="application/pdf",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(data)),
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Cache-Control": "private, max-age=60",
        },
    )


def _parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    if not header:
        return None
    match = _RANGE_RE.match(header.strip())
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else size - 1
    if start >= size or start > end:
        return None
    return start, min(end, size - 1)
