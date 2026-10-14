from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth_proxy import (
    firebase_helper_origin,
    helper_response,
    is_helper_path,
    rewrite_set_cookie,
    router,
)


def test_firebase_helper_origin_uses_project_id(monkeypatch):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "kirjasto-celssi")
    assert firebase_helper_origin() == "https://kirjasto-celssi.firebaseapp.com"


def test_is_helper_path():
    assert is_helper_path("/__/auth/handler")
    assert is_helper_path("/__/auth")
    assert is_helper_path("/__/firebase/init.json")
    assert not is_helper_path("/__/secret")
    assert not is_helper_path("/api/health")


def test_rewrite_set_cookie_drops_upstream_domain():
    raw = "session=abc; Domain=kirjasto-celssi.firebaseapp.com; Path=/; Secure; SameSite=None"
    rewritten = rewrite_set_cookie(raw)
    assert "Domain=" not in rewritten
    assert "session=abc" in rewritten
    assert "Path=/" in rewritten
    assert "SameSite=None" in rewritten


def test_helper_response_rewrites_cookies_and_keeps_location():
    response = helper_response(
        302,
        [
            ("Location", "https://accounts.google.com/o"),
            ("Set-Cookie", "sid=1; Domain=kirjasto-celssi.firebaseapp.com; Path=/"),
            ("Content-Type", "text/html"),
        ],
        b"",
    )
    assert response.status_code == 302
    assert response.headers["location"] == "https://accounts.google.com/o"
    assert "Domain=" not in response.headers.get("set-cookie", "")
    assert "sid=1" in response.headers.get("set-cookie", "")


def test_proxy_forwards_query_and_body(monkeypatch):
    captured: dict = {}

    def fake_fetch(method, url, headers, body, timeout=20):
        captured.update({"method": method, "url": url, "headers": headers, "body": body})
        return 200, [("Content-Type", "text/html")], b"handler"

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "kirjasto-celssi")
    monkeypatch.setattr("backend.auth_proxy.fetch_helper", fake_fetch)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    res = client.post(
        "/__/auth/handler?apiKey=test",
        content=b"code=1",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert res.status_code == 200
    assert res.text == "handler"
    assert captured["method"] == "POST"
    assert captured["url"] == "https://kirjasto-celssi.firebaseapp.com/__/auth/handler?apiKey=test"
    assert captured["body"] == b"code=1"


def test_proxy_rejects_traversal(monkeypatch):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "kirjasto-celssi")
    monkeypatch.setattr(
        "backend.auth_proxy.fetch_helper",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not fetch")),
    )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    res = client.get("/__/auth/foo/../../secret")

    assert res.status_code == 404
