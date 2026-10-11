from backend.routes.system import keepalive


def test_keepalive_payload():
    payload = keepalive()
    assert payload["ok"] is True
    assert isinstance(payload["ts"], int)
