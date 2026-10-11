from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.main import SPAStaticFiles


def test_spa_unknown_path_serves_index(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html>auto-dm</html>")
    app = FastAPI()
    app.mount("/", SPAStaticFiles(directory=str(tmp_path), html=True), name="frontend")
    client = TestClient(app)

    res = client.get("/characters")

    assert res.status_code == 200
    assert res.text == "<html>auto-dm</html>"


def test_spa_missing_asset_still_404(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html>auto-dm</html>")
    app = FastAPI()
    app.mount("/", SPAStaticFiles(directory=str(tmp_path), html=True), name="frontend")
    client = TestClient(app)

    res = client.get("/assets/missing.js")

    assert res.status_code == 404
