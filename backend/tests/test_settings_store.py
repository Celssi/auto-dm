"""Persisted settings drop unknown keys such as chat_model."""

from backend.settings_store import DEFAULTS, load_settings, save_settings


def test_load_settings_drops_chat_model(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"include_faerun": true, "chat_model": "claude-opus-4-6"}', encoding="utf-8")
    monkeypatch.setattr("backend.settings_store.PREFS_PATH", path)
    loaded = load_settings()
    assert "chat_model" not in loaded
    assert loaded["include_faerun"] is True
    assert loaded["use_rerank"] is DEFAULTS["use_rerank"]


def test_save_settings_does_not_persist_chat_model(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    monkeypatch.setattr("backend.settings_store.PREFS_PATH", path)
    saved = save_settings({"use_rerank": False, "chat_model": "ignored"})
    assert "chat_model" not in saved
    assert saved["use_rerank"] is False
    on_disk = path.read_text(encoding="utf-8")
    assert "chat_model" not in on_disk
