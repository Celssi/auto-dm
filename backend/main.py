"""Auto-DM FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.auth import is_public_api_path, require_allowed_user
from backend.config import LANGSMITH_ENABLED, LANGSMITH_ENDPOINT, LANGSMITH_PROJECT
from backend.gcs_sync import hydrate_runtime
from backend.routes import adventures, brambletrek, campaigns, characters, play, sessions, system

logger = logging.getLogger(__name__)


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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"],
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
    return await call_next(request)

app.include_router(system.router)
app.include_router(characters.router)
app.include_router(campaigns.router)
app.include_router(adventures.router)
app.include_router(play.router)
app.include_router(brambletrek.router)
app.include_router(sessions.router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
