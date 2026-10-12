"""In-app rulebook PDF API."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from backend.auth import (
    allowed_emails,
    bearer_token,
    is_local_dev_bypass,
    require_allowed_user,
    verify_id_token,
)
from backend.book_catalog import list_books, resolve_book
from backend.book_store import load_book_state, save_book_state
from backend.config import local_pdf_path
from backend.gcs_sync import pdf_byte_size, read_pdf_bytes

router = APIRouter(prefix="/api/books", tags=["books"])

_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")
_TICKET_TTL_SEC = 30 * 60
_MAX_RANGE_BYTES = 2 * 1024 * 1024
_FIRST_CHUNK = 64 * 1024
_STREAM_CHUNK = 256 * 1024


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


def _ticket_secret() -> bytes:
    raw = (
        os.environ.get("AUTO_DM_TICKET_SECRET")
        or os.environ.get("ANTHROPIC_API_KEY")
        or "auto-dm-local-ticket"
    )
    return raw.encode()


def issue_file_ticket(book_id: str, ttl: int = _TICKET_TTL_SEC) -> str:
    exp = int(time.time()) + ttl
    digest = hmac.new(_ticket_secret(), f"{book_id}:{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{digest}"


def verify_file_ticket(ticket: str, book_id: str) -> bool:
    try:
        exp_s, digest = ticket.split(".", 1)
        exp = int(exp_s)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    expected = hmac.new(_ticket_secret(), f"{book_id}:{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)


def _can_read_file(request: Request, book_id: str) -> bool:
    if is_local_dev_bypass(request):
        return True
    ticket = request.query_params.get("ticket")
    if ticket and verify_file_ticket(ticket, book_id):
        return True
    token = bearer_token(request)
    if not token:
        return False
    try:
        decoded = verify_id_token(token)
    except Exception:
        return False
    email = str(decoded.get("email") or "").strip().lower()
    return bool(email and email in allowed_emails())


def _pdf_headers(size: int | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=60",
        "Access-Control-Expose-Headers": "Accept-Ranges, Content-Range, Content-Length",
    }
    if size is not None:
        headers["Content-Length"] = str(size)
    if extra:
        headers.update(extra)
    return headers


def _iter_pdf_bytes(book_id: str, start: int, end: int):
    offset = start
    while offset <= end:
        stop = min(offset + _STREAM_CHUNK - 1, end)
        yield read_pdf_bytes(book_id, offset, stop)
        offset = stop + 1


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
        updates["lastByGame"] = {
            game_id: item.model_dump() for game_id, item in body.lastByGame.items()
        }
    return save_book_state(updates)


@router.get("/{book_id:path}/ticket")
async def book_file_ticket(book_id: str, request: Request, game_id: str = Query(default="dnd5e")):
    await require_allowed_user(request)
    book = resolve_book(game_id, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"ticket": issue_file_ticket(book_id), "expires_in": _TICKET_TTL_SEC}


@router.api_route("/{book_id:path}/file", methods=["GET", "HEAD"])
def book_file(book_id: str, request: Request, game_id: str = Query(default="dnd5e")):
    if not _can_read_file(request, book_id):
        raise HTTPException(status_code=401, detail="Sign-in required")
    book = resolve_book(game_id, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    local = local_pdf_path(book_id)
    if local.is_file():
        if request.method == "HEAD":
            return Response(
                status_code=200,
                media_type="application/pdf",
                headers=_pdf_headers(local.stat().st_size),
            )
        return FileResponse(
            local,
            media_type="application/pdf",
            filename=local.name,
            headers=_pdf_headers(),
        )

    size = pdf_byte_size(book_id)
    if size is None or size <= 0:
        raise HTTPException(status_code=404, detail="Book file not available")

    if request.method == "HEAD":
        return Response(status_code=200, media_type="application/pdf", headers=_pdf_headers(size))

    parsed = _parse_range(request.headers.get("range"), size)
    if parsed is None:
        if size <= _FIRST_CHUNK:
            data = read_pdf_bytes(book_id)
            return Response(
                content=data,
                media_type="application/pdf",
                headers=_pdf_headers(len(data)),
            )
        parsed = (0, _FIRST_CHUNK - 1)

    start, end = parsed
    if end - start + 1 > _MAX_RANGE_BYTES:
        end = start + _MAX_RANGE_BYTES - 1
    length = end - start + 1
    return StreamingResponse(
        _iter_pdf_bytes(book_id, start, end),
        status_code=206,
        media_type="application/pdf",
        headers=_pdf_headers(
            length,
            {"Content-Range": f"bytes {start}-{end}/{size}"},
        ),
    )


def _parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    if not header:
        return None
    match = _RANGE_RE.match(header.strip())
    if not match:
        return None
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else min(start + _MAX_RANGE_BYTES - 1, size - 1)
    if start >= size or start > end:
        return None
    return start, min(end, size - 1)
