from backend.auth import allowed_emails, is_public_api_path


def test_default_allowed_email(monkeypatch):
    monkeypatch.delenv("ALLOWED_EMAILS", raising=False)
    assert "lauri.mukkala.fi@gmail.com" in allowed_emails()


def test_allowed_emails_from_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAILS", "lauri.mukkala.fi@gmail.com, other@example.com")
    assert allowed_emails() == {"lauri.mukkala.fi@gmail.com", "other@example.com"}


def test_health_is_public():
    assert is_public_api_path("/api/health")
    assert not is_public_api_path("/api/characters")
