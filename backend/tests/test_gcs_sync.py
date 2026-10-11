from pathlib import Path

from backend.gcs_sync import bucket_enabled, download_pdf, hydrate_runtime, upload_saves_path


def test_bucket_disabled_without_env(monkeypatch):
    monkeypatch.delenv("AUTO_DM_BUCKET", raising=False)
    assert bucket_enabled() is False


def test_helpers_are_noops_without_bucket(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("AUTO_DM_BUCKET", raising=False)
    hydrate_runtime()
    upload_saves_path(tmp_path / "missing.json")
    dest = tmp_path / "player.pdf"
    assert download_pdf("dnd5e/player.pdf", dest) == dest
    assert not dest.exists()
