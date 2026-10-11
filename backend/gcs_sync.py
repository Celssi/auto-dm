"""Cloud Storage helpers for PDFs, Chroma, and save files."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.config import CHROMA_DIR, DATA_DIR, SAVES_DIR

logger = logging.getLogger(__name__)

PDF_PREFIX = "pdfs/"
CHROMA_PREFIX = "chroma/"
SAVES_PREFIX = "saves/"


def data_bucket_name() -> str:
    return os.environ.get("AUTO_DM_BUCKET", "").strip()


def bucket_enabled() -> bool:
    return bool(data_bucket_name())


def _client():
    from google.cloud import storage

    return storage.Client()


def _bucket():
    name = data_bucket_name()
    if not name:
        return None
    return _client().bucket(name)


def _relative_to(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def upload_blob(object_name: str, local_path: Path) -> None:
    bucket = _bucket()
    if bucket is None or not local_path.is_file():
        return
    blob = bucket.blob(object_name)
    blob.upload_from_filename(str(local_path))
    logger.debug("Uploaded gs://%s/%s", data_bucket_name(), object_name)


def download_blob(object_name: str, local_path: Path) -> bool:
    bucket = _bucket()
    if bucket is None:
        return False
    blob = bucket.blob(object_name)
    if not blob.exists():
        return False
    local_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local_path))
    return True


def delete_blob(object_name: str) -> None:
    bucket = _bucket()
    if bucket is None:
        return
    blob = bucket.blob(object_name)
    try:
        blob.delete()
    except Exception:
        logger.debug("Could not delete gs://%s/%s", data_bucket_name(), object_name)


def download_prefix(prefix: str, dest: Path) -> int:
    bucket = _bucket()
    if bucket is None:
        return 0
    count = 0
    for blob in _client().list_blobs(data_bucket_name(), prefix=prefix):
        if blob.name.endswith("/"):
            continue
        rel = blob.name[len(prefix) :] if blob.name.startswith(prefix) else blob.name
        if not rel:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target))
        count += 1
    return count


def upload_prefix(local_dir: Path, prefix: str) -> int:
    bucket = _bucket()
    if bucket is None or not local_dir.is_dir():
        return 0
    count = 0
    for path in local_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(local_dir).as_posix()
        upload_blob(f"{prefix}{rel}", path)
        count += 1
    return count


def delete_prefix(prefix: str) -> None:
    bucket = _bucket()
    if bucket is None:
        return
    for blob in _client().list_blobs(data_bucket_name(), prefix=prefix):
        blob.delete()


def download_pdf(relative: str, dest: Path) -> Path:
    if dest.exists() or not bucket_enabled():
        return dest
    object_name = f"{PDF_PREFIX}{relative.lstrip('/')}"
    if download_blob(object_name, dest):
        logger.info("Downloaded PDF %s", object_name)
    return dest


def upload_saves_path(path: Path) -> None:
    if not bucket_enabled():
        return
    if path.resolve() == (DATA_DIR / "settings.json").resolve():
        upload_blob(f"{SAVES_PREFIX}settings.json", path)
        return
    rel = _relative_to(path, SAVES_DIR)
    if rel:
        upload_blob(f"{SAVES_PREFIX}{rel}", path)
        return
    rel = _relative_to(path, CHROMA_DIR)
    if rel:
        upload_blob(f"{CHROMA_PREFIX}{rel}", path)


def delete_saves_path(path: Path) -> None:
    if not bucket_enabled():
        return
    rel = _relative_to(path, SAVES_DIR)
    if rel:
        if path.is_dir() or not path.suffix:
            delete_prefix(f"{SAVES_PREFIX}{rel.rstrip('/')}/")
        else:
            delete_blob(f"{SAVES_PREFIX}{rel}")


def upload_chroma() -> None:
    if not bucket_enabled():
        return
    delete_prefix(CHROMA_PREFIX)
    upload_prefix(CHROMA_DIR, CHROMA_PREFIX)


def hydrate_runtime() -> None:
    if not bucket_enabled():
        return
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    chroma_count = download_prefix(CHROMA_PREFIX, CHROMA_DIR)
    saves_count = download_prefix(SAVES_PREFIX, SAVES_DIR)
    settings_src = SAVES_DIR / "settings.json"
    if settings_src.is_file():
        dest = DATA_DIR / "settings.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(settings_src.read_bytes())
    logger.info("Hydrated runtime from gs://%s (chroma=%s, saves=%s)", data_bucket_name(), chroma_count, saves_count)
