"""Cloud Storage helpers for PDFs, Chroma, and save files."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from backend.config import CHROMA_DIR, DATA_DIR, SAVES_DIR, _load_dotenv_value, local_pdf_path

logger = logging.getLogger(__name__)

PDF_PREFIX = "pdfs/"
CHROMA_PREFIX = "chroma/"
SAVES_PREFIX = "saves/"
DEFAULT_BUCKET = "celssi-auto-dm"
_DISABLED_BUCKETS = {"", "none", "local", "off", "0", "false"}


def data_bucket_name() -> str:
    raw = os.environ.get("AUTO_DM_BUCKET")
    if raw is None:
        raw = _load_dotenv_value("AUTO_DM_BUCKET") or DEFAULT_BUCKET
    name = (raw or "").strip()
    if name.lower() in _DISABLED_BUCKETS:
        return ""
    return name


def bucket_enabled() -> bool:
    return bool(data_bucket_name())


def _gcs_project() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT") or "celssi"
    ).strip()


def _local_gcs_credentials():
    """Use the allowed account's gcloud login when ADC is a different user."""
    from google.oauth2.credentials import Credentials

    from backend.auth import DEFAULT_ALLOWED_EMAIL, allowed_emails

    account = (
        os.environ.get("AUTO_DM_GCLOUD_ACCOUNT")
        or os.environ.get("CLOUDSDK_CORE_ACCOUNT")
        or next(iter(allowed_emails()), DEFAULT_ALLOWED_EMAIL)
    ).strip()
    adc_path = Path.home() / ".config/gcloud/legacy_credentials" / account / "adc.json"
    if not adc_path.is_file():
        return None
    info = json.loads(adc_path.read_text(encoding="utf-8"))
    logger.info("Using gcloud credentials for %s", account)
    return Credentials.from_authorized_user_info(info)


@lru_cache(maxsize=1)
def _client():
    from google.cloud import storage

    project = _gcs_project()
    if os.environ.get("K_SERVICE"):
        return storage.Client(project=project)
    creds = _local_gcs_credentials()
    if creds is not None:
        return storage.Client(project=project, credentials=creds)
    return storage.Client(project=project)


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


def pdf_object_name(relative: str) -> str:
    return f"{PDF_PREFIX}{relative.lstrip('/')}"


def pdf_available(relative: str) -> bool:
    if local_pdf_path(relative).is_file():
        return True
    bucket = _bucket()
    if bucket is None:
        return False
    return bool(bucket.blob(pdf_object_name(relative)).exists())


def pdf_byte_size(relative: str) -> int | None:
    local = local_pdf_path(relative)
    if local.is_file():
        return local.stat().st_size
    bucket = _bucket()
    if bucket is None:
        return None
    blob = bucket.blob(pdf_object_name(relative))
    if not blob.exists():
        return None
    blob.reload()
    return int(blob.size or 0)


def read_pdf_bytes(relative: str, start: int = 0, end: int | None = None) -> bytes:
    local = local_pdf_path(relative)
    if local.is_file():
        with local.open("rb") as handle:
            handle.seek(start)
            if end is None:
                return handle.read()
            return handle.read(end - start + 1)
    bucket = _bucket()
    if bucket is None:
        raise FileNotFoundError(relative)
    blob = bucket.blob(pdf_object_name(relative))
    if not blob.exists():
        raise FileNotFoundError(relative)
    if end is None:
        return blob.download_as_bytes(start=start)
    return blob.download_as_bytes(start=start, end=end)


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
    try:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        hydrate_chroma = bool(os.environ.get("K_SERVICE")) or (
            os.environ.get("AUTO_DM_HYDRATE_CHROMA") == "1"
        )
        chroma_count = download_prefix(CHROMA_PREFIX, CHROMA_DIR) if hydrate_chroma else 0
        saves_count = download_prefix(SAVES_PREFIX, SAVES_DIR)
        settings_src = SAVES_DIR / "settings.json"
        if settings_src.is_file():
            dest = DATA_DIR / "settings.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(settings_src.read_bytes())
        logger.info(
            "Hydrated runtime from gs://%s (chroma=%s, saves=%s)",
            data_bucket_name(),
            chroma_count,
            saves_count,
        )
    except Exception:
        if os.environ.get("K_SERVICE"):
            raise
        logger.exception("Could not hydrate from gs://%s, using local saves", data_bucket_name())
