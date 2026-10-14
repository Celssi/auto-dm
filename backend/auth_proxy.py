"""Same-origin Firebase Auth helper so Google sign-in can finish on the app domain."""

from __future__ import annotations

import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, Request, Response

from backend.auth import firebase_project_id

logger = logging.getLogger(__name__)

HELPER_PREFIXES = ("/__/auth", "/__/firebase")
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}
FORWARDED_REQUEST_HEADERS = {
    "accept",
    "accept-language",
    "content-type",
    "cookie",
    "origin",
    "referer",
    "user-agent",
}
FORWARDED_RESPONSE_HEADERS = {
    "cache-control",
    "content-disposition",
    "content-type",
    "expires",
    "location",
    "pragma",
}

router = APIRouter()


def firebase_helper_origin() -> str:
    return f"https://{firebase_project_id()}.firebaseapp.com"


def rewrite_set_cookie(value: str) -> str:
    """Drop Domain so the helper cookie is stored on the app origin."""
    kept: list[str] = []
    for part in value.split(";"):
        if part.strip().lower().startswith("domain="):
            continue
        kept.append(part)
    return ";".join(kept)


def is_helper_path(path: str) -> bool:
    return path == "/__/auth" or path == "/__/firebase" or path.startswith(("/__/auth/", "/__/firebase/"))


def _request_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() in FORWARDED_REQUEST_HEADERS:
            headers[key] = value
    return headers


def fetch_helper(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: float = 20,
) -> tuple[int, list[tuple[str, str]], bytes]:
    request = Request(url, data=body or None, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as upstream:
            status = upstream.status
            raw_headers = list(upstream.headers.items())
            payload = upstream.read()
    except HTTPError as exc:
        status = exc.code
        raw_headers = list(exc.headers.items()) if exc.headers is not None else []
        payload = exc.read()
    return status, raw_headers, payload


def helper_response(status: int, raw_headers: list[tuple[str, str]], payload: bytes) -> Response:
    response = Response(content=payload, status_code=status)
    for key, value in raw_headers:
        lower = key.lower()
        if lower in HOP_BY_HOP:
            continue
        if lower == "set-cookie":
            response.headers.append("set-cookie", rewrite_set_cookie(value))
            continue
        if lower in FORWARDED_RESPONSE_HEADERS:
            response.headers[key] = value
    return response


@router.api_route("/__/auth", methods=["GET", "POST", "HEAD", "OPTIONS"])
@router.api_route("/__/firebase", methods=["GET", "POST", "HEAD", "OPTIONS"])
@router.api_route("/__/auth/{path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
@router.api_route("/__/firebase/{path:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def firebase_auth_helper(request: Request, path: str = "") -> Response:
    del path
    pathname = request.url.path
    if ".." in pathname or not is_helper_path(pathname):
        raise HTTPException(status_code=404, detail="Not found")
    target = f"{firebase_helper_origin()}{pathname}"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    body = await request.body()
    try:
        status, raw_headers, payload = fetch_helper(
            request.method,
            target,
            _request_headers(request),
            body if body else None,
        )
    except URLError as exc:
        logger.warning("Firebase auth helper proxy failed: %s", exc)
        raise HTTPException(status_code=502, detail="Google sign-in helper is unavailable") from exc
    return helper_response(status, raw_headers, payload)
