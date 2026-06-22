"""Project paths and model settings for auto-dm."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "dnd5e"
DATA_DIR = ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"
CURATED_DIR = DATA_DIR / "curated"
SAVES_DIR = DATA_DIR / "saves"
OCR_CACHE_DIR = DATA_DIR / "ocr_cache"

COLLECTION_NAME = "dnd5e_rules"

OCR_MIN_CHARS_SAMPLE = 200
OCR_RENDER_DPI = 300
TESSERACT_LANG = "eng"
TESSERACT_CONFIG = "--oem 1 --psm 3"

OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
EMBED_DOCUMENT_PREFIX = "search_document: "
EMBED_QUERY_PREFIX = "search_query: "
OLLAMA_REQUEST_TIMEOUT = float(os.environ.get("OLLAMA_REQUEST_TIMEOUT", "600"))

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
TOP_K_DEFAULT = 5
RERANK_MODEL = os.environ.get("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")


def _load_dotenv_value(name: str) -> str | None:
    if os.environ.get(name, "").strip():
        return os.environ[name].strip()
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return None
    prefix = f"{name}="
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix) :].strip().strip("'\"")
        if value:
            os.environ[name] = value
            return value
    return None


ANTHROPIC_API_KEY = _load_dotenv_value("ANTHROPIC_API_KEY")
CLAUDE_CHAT_MODEL = os.environ.get("CLAUDE_CHAT_MODEL", "claude-opus-4-6")
CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "gemma3:12b")


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def configure_langsmith() -> dict[str, str | bool]:
    """Enable LangSmith tracing when an API key is configured."""
    api_key = _load_dotenv_value("LANGSMITH_API_KEY") or _load_dotenv_value("LANGCHAIN_API_KEY")
    if not api_key:
        return {"enabled": False, "project": "", "endpoint": ""}

    tracing_requested = _env_truthy("LANGSMITH_TRACING") or _env_truthy("LANGCHAIN_TRACING_V2")
    if os.environ.get("LANGSMITH_TRACING") is None and os.environ.get("LANGCHAIN_TRACING_V2") is None:
        tracing_requested = True
    if not tracing_requested:
        return {"enabled": False, "project": "", "endpoint": ""}

    project = (
        os.environ.get("LANGSMITH_PROJECT")
        or os.environ.get("LANGCHAIN_PROJECT")
        or "Auto DM Tracing Project"
    ).strip()

    endpoint = (
        os.environ.get("LANGSMITH_ENDPOINT")
        or os.environ.get("LANGCHAIN_ENDPOINT")
        or "https://eu.api.smith.langchain.com"
    ).strip()

    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGSMITH_ENDPOINT"] = endpoint
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    return {"enabled": True, "project": project, "endpoint": endpoint}


_LANGSMITH = configure_langsmith()
LANGSMITH_ENABLED: bool = bool(_LANGSMITH["enabled"])
LANGSMITH_PROJECT: str = str(_LANGSMITH.get("project") or "")
LANGSMITH_ENDPOINT: str = str(_LANGSMITH.get("endpoint") or "")

# PDF sources relative to PDF_DIR parent (dnd5e/ folder)
PDF_SOURCES: dict[str, dict[str, str]] = {
    "dnd5e/player.pdf": {"faction": "player", "label": "Player's Handbook (2024)"},
    "dnd5e/dm.pdf": {"faction": "dm", "label": "Dungeon Master's Guide (2024)"},
    "dnd5e/monsters.pdf": {"faction": "monsters", "label": "Monster Manual (2024)"},
    "dnd5e/heroes_faerun.pdf": {"faction": "heroes_faerun", "label": "Heroes of Faerûn"},
    "dnd5e/adventures_faerun.pdf": {
        "faction": "adventures_faerun",
        "label": "Adventures in Faerûn",
    },
}

CORE_PDFS = ["dnd5e/player.pdf", "dnd5e/dm.pdf", "dnd5e/monsters.pdf"]
FAERUN_PDFS = ["dnd5e/heroes_faerun.pdf", "dnd5e/adventures_faerun.pdf"]
ALL_FACTIONS = ["player", "dm", "monsters", "heroes_faerun", "adventures_faerun"]
OCR_PDFS = ["dnd5e/player.pdf", "dnd5e/monsters.pdf"]

# PDF paths on disk (PDF_DIR is dnd5e/, keys use dnd5e/ prefix)
DOCS_DIR = ROOT


def pdf_path(relative: str) -> Path:
    """Resolve dnd5e/foo.pdf to ROOT/dnd5e/foo.pdf."""
    if relative.startswith("dnd5e/"):
        return ROOT / relative
    return PDF_DIR / relative
