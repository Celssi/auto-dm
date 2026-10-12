from pathlib import Path

from backend.gcs_sync import (
    bucket_enabled,
    data_bucket_name,
    download_pdf,
    hydrate_runtime,
    upload_saves_path,
)


def test_default_bucket_is_production(monkeypatch):
    monkeypatch.delenv("AUTO_DM_BUCKET", raising=False)
    assert data_bucket_name() == "celssi-auto-dm"
    assert bucket_enabled() is True


def test_empty_bucket_disables(monkeypatch):
    monkeypatch.setenv("AUTO_DM_BUCKET", "")
    assert data_bucket_name() == ""
    assert bucket_enabled() is False


def test_helpers_are_noops_without_bucket(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AUTO_DM_BUCKET", "")
    hydrate_runtime()
    upload_saves_path(tmp_path / "missing.json")
    dest = tmp_path / "player.pdf"
    assert download_pdf("dnd5e/player.pdf", dest) == dest
    assert not dest.exists()
