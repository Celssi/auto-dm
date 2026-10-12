import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.auth import (
    allowed_emails,
    is_local_dev_bypass,
    is_public_api_path,
    require_allowed_user,
)


def _request(host: str = "127.0.0.1", origin: str | None = None) -> Request:
    headers = []
    if origin:
        headers.append((b"origin", origin.encode()))
    return Request(
        {
            "type": "http",
            "asgi": {"spec_version": "2.1", "version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/characters",
            "raw_path": b"/api/characters",
            "query_string": b"",
            "headers": headers,
            "client": (host, 12345),
            "server": ("127.0.0.1", 8000),
        }
    )


def test_default_allowed_email(monkeypatch):
    monkeypatch.delenv("ALLOWED_EMAILS", raising=False)
    assert "lauri.mukkala.fi@gmail.com" in allowed_emails()


def test_allowed_emails_from_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_EMAILS", "lauri.mukkala.fi@gmail.com, other@example.com")
    assert allowed_emails() == {"lauri.mukkala.fi@gmail.com", "other@example.com"}


def test_health_is_public():
    assert is_public_api_path("/api/health")
    assert is_public_api_path("/api/books/dnd5e/player.pdf/file")
    assert not is_public_api_path("/api/books/dnd5e/player.pdf/ticket")
    assert not is_public_api_path("/api/characters")


def test_local_bypass_for_loopback(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("AUTO_DM_REQUIRE_AUTH", raising=False)
    assert is_local_dev_bypass(_request())


def test_local_bypass_off_on_cloud_run(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "auto-dm")
    assert not is_local_dev_bypass(_request())


def test_local_bypass_off_when_auth_required(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.setenv("AUTO_DM_REQUIRE_AUTH", "1")
    assert not is_local_dev_bypass(_request())


def test_require_allowed_user_skips_token_locally(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("AUTO_DM_REQUIRE_AUTH", raising=False)
    user = asyncio.run(require_allowed_user(_request()))
    assert user["email"] == "lauri.mukkala.fi@gmail.com"
    assert user["uid"] == "local-dev"


def test_require_allowed_user_needs_token_on_cloud_run(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "auto-dm")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_allowed_user(_request()))
    assert exc.value.status_code == 401
