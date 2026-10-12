"""Firebase ID token checks for the Cloud Run API."""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import HTTPException, Request

DEFAULT_ALLOWED_EMAIL = "lauri.mukkala.fi@gmail.com"
PUBLIC_API_PATHS = {"/api/health"}


def allowed_emails() -> set[str]:
    raw = os.environ.get("ALLOWED_EMAILS", DEFAULT_ALLOWED_EMAIL)
    emails = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return emails or {DEFAULT_ALLOWED_EMAIL}


def firebase_project_id() -> str:
    return (
        os.environ.get("FIREBASE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or "celssi"
    ).strip()


@lru_cache(maxsize=1)
def _firebase_app():
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return firebase_admin.get_app()
    cred = credentials.ApplicationDefault()
    return firebase_admin.initialize_app(cred, {"projectId": firebase_project_id()})


def verify_id_token(token: str) -> dict:
    from firebase_admin import auth

    _firebase_app()
    return auth.verify_id_token(token)


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        return None
    token = header[7:].strip()
    return token or None


def is_local_dev_bypass(request: Request) -> bool:
    """Skip Firebase only for loopback uvicorn, never on Cloud Run."""
    if os.environ.get("K_SERVICE"):
        return False
    if os.environ.get("AUTO_DM_REQUIRE_AUTH") == "1":
        return False
    client = (request.client.host if request.client else "") or ""
    if client in {"127.0.0.1", "::1", "localhost"}:
        return True
    origin = (request.headers.get("origin") or "").lower()
    return origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")


async def require_allowed_user(request: Request) -> dict:
    if is_local_dev_bypass(request):
        email = next(iter(allowed_emails()))
        return {"uid": "local-dev", "email": email}
    token = bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Sign-in required")
    try:
        decoded = verify_id_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc
    email = str(decoded.get("email") or "").strip().lower()
    if not email or email not in allowed_emails():
        raise HTTPException(status_code=403, detail="Access denied")
    return {"uid": decoded.get("uid"), "email": email}


def is_book_file_path(path: str) -> bool:
    return path.startswith("/api/books/") and path.endswith("/file")


def is_public_api_path(path: str) -> bool:
    return path in PUBLIC_API_PATHS or is_book_file_path(path)
