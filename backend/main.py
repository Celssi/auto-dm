"""Auto-DM FastAPI application."""

from __future__ import annotations

import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from backend.auth import is_public_api_path, require_allowed_user
from backend.config import LANGSMITH_ENABLED, LANGSMITH_ENDPOINT, LANGSMITH_PROJECT
from backend.gcs_sync import hydrate_runtime
from backend.routes import (
    adventures,
    books,
    brambletrek,
    campaigns,
    characters,
    play,
    sessions,
    system,
)

mimetypes.add_type("text/javascript", ".mjs")

logger = logging.getLogger(__name__)

# Chrome severs window.opener when this page's opener policy does not match
# Google's account chooser. Firebase then reports auth/popup-closed-by-user
# after the account is picked. This value keeps the sign-in popup attached.
AUTH_POPUP_COOP = "same-origin-allow-popups"


def apply_auth_popup_headers(response) -> None:
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/html"):
        response.headers["Cross-Origin-Opener-Policy"] = AUTH_POPUP_COOP


@asynccontextmanager
async def lifespan(_app: FastAPI):
    hydrate_runtime()
    yield


app = FastAPI(title="auto-dm", version="0.1.0", lifespan=lifespan)

if LANGSMITH_ENABLED:
    logger.info(
        "LangSmith tracing enabled (project=%s, endpoint=%s)",
        LANGSMITH_PROJECT,
        LANGSMITH_ENDPOINT,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "https://autodm.celssi.fi",
    ],
    allow_origin_regex=r"https://.*\.run\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def firebase_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if path.startswith("/api") and not is_public_api_path(path):
        try:
            await require_allowed_user(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    response = await call_next(request)
    apply_auth_popup_headers(response)
    return response


app.include_router(system.router)
app.include_router(books.router)
app.include_router(characters.router)
app.include_router(campaigns.router)
app.include_router(adventures.router)
app.include_router(play.router)
app.include_router(brambletrek.router)
app.include_router(sessions.router)


class SPAStaticFiles(StarletteStaticFiles):
    """Serve index.html for client-side routes such as /characters."""

    _spa_prefixes = {"characters", "campaigns", "adventures", "play", "books", "settings"}

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            name = path.rsplit("/", 1)[-1]
            first = path.split("/", 1)[0]
            spa_fallback = "." not in name or first in self._spa_prefixes
            if exc.status_code == 404 and path != "index.html" and spa_fallback:
                response = await super().get_response("index.html", scope)
                apply_auth_popup_headers(response)
                return response
            raise
        if path == "sw.js":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Service-Worker-Allowed"] = "/"
        apply_auth_popup_headers(response)
        return response


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")
