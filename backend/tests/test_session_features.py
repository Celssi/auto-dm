"""Session recap, world roster, rename, and archive."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import journal_storage, storage
from backend.dm.session_recap import fallback_recap, get_or_refresh_recap
from backend.dm.session_world import extract_marked_names, get_or_refresh_world
from backend.routes.sessions import router


@pytest.fixture(autouse=True)
def disable_gcs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTO_DM_BUCKET", "")


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _session(name: str = "Night at the inn") -> str:
    storage.save_character("hero", {"name": "Hero", "game_id": "dnd5e"})
    adv_id = storage.save_adventure("adv1", {"name": "Quest", "character_id": "hero"})
    return storage.create_session(character_id="hero", adventure_id=adv_id, name=name)


def test_list_sessions_hides_archived_by_default(isolated_saves):
    sid = _session()
    storage.patch_session(sid, {"archived": True})

    assert [s["id"] for s in storage.list_sessions()] == []
    hidden = storage.list_sessions(include_archived=True)
    assert len(hidden) == 1
    assert hidden[0]["id"] == sid
    assert hidden[0]["archived"] is True


def test_legacy_index_row_without_archived_still_lists(isolated_saves):
    sid = _session()
    index = storage._read_json(storage.SESSIONS_INDEX, [])
    for row in index:
        row.pop("archived", None)
    storage._write_json(storage.SESSIONS_INDEX, index)

    listed = storage.list_sessions()
    assert listed[0]["id"] == sid
    assert "archived" not in listed[0]


def test_rename_updates_session_and_index(isolated_saves):
    sid = _session()
    storage.patch_session(sid, {"name": "The burned mill"})

    sess = storage.get_session(sid)
    assert sess and sess["name"] == "The burned mill"
    assert storage.list_sessions()[0]["name"] == "The burned mill"


def test_empty_rename_rejected(isolated_saves):
    sid = _session()
    try:
        storage.patch_session(sid, {"name": "   "})
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    assert storage.get_session(sid)["name"] == "Night at the inn"


def test_unarchive_returns_session_to_default_list(isolated_saves):
    sid = _session()
    storage.patch_session(sid, {"archived": True})
    storage.patch_session(sid, {"archived": False})
    assert storage.list_sessions()[0]["id"] == sid
    assert storage.get_session(sid).get("archived") is False


def test_find_session_for_adventure_skips_archived(isolated_saves):
    sid = _session()
    adv_id = storage.get_session(sid)["adventure_id"]
    assert storage.find_session_for_adventure(adv_id)["id"] == sid
    storage.patch_session(sid, {"archived": True})
    assert storage.find_session_for_adventure(adv_id) is None


def test_cascade_delete_includes_archived_sessions(isolated_saves):
    sid = _session()
    adv_id = storage.get_session(sid)["adventure_id"]
    storage.patch_session(sid, {"archived": True})
    assert storage.delete_adventure(adv_id)
    assert storage.get_session(sid) is None
    assert storage.list_sessions(include_archived=True) == []


def test_fallback_recap_uses_recent_assistant_turns():
    text = fallback_recap(
        messages=[
            {"role": "user", "content": "I open the door."},
            {"role": "assistant", "content": "A tavern hush falls as you step inside."},
            {"role": "user", "content": "I ask for a room."},
            {"role": "assistant", "content": "The innkeeper nods and tosses you a brass key."},
        ]
    )
    assert "brass key" in text
    assert "—" not in text
    assert "–" not in text


def test_recap_cached_until_new_messages(isolated_saves):
    sid = _session()
    storage.save_session_messages(
        sid,
        [
            {"role": "assistant", "content": "Rain hits the cobbles as you reach the gate."},
        ],
    )

    recap_text = "You reached the city gate in the rain."
    with patch("backend.dm.session_recap.generate_recap", return_value=recap_text) as gen:
        first = get_or_refresh_recap(sid)
        second = get_or_refresh_recap(sid)
        assert gen.call_count == 1
    assert first["text"] == recap_text
    assert second["text"] == first["text"]
    assert first["message_count"] == 1

    storage.save_session_messages(
        sid,
        [
            {"role": "assistant", "content": "Rain hits the cobbles as you reach the gate."},
            {"role": "user", "content": "I look for a stable."},
            {"role": "assistant", "content": "A boy takes the reins."},
        ],
    )
    later = "A stable boy took the reins."
    with patch("backend.dm.session_recap.generate_recap", return_value=later) as gen:
        third = get_or_refresh_recap(sid)
        assert gen.call_count == 1
    assert third["text"] == later
    assert third["message_count"] == 3


def test_recap_falls_back_when_llm_fails(isolated_saves):
    sid = _session()
    storage.save_session_messages(
        sid,
        [{"role": "assistant", "content": "You hide behind the mill wheel."}],
    )
    with patch("backend.dm.session_recap.generate_recap", side_effect=RuntimeError("no key")):
        recap = get_or_refresh_recap(sid)
    assert "mill wheel" in recap["text"]


def test_empty_session_has_no_recap(isolated_saves):
    sid = _session()
    recap = get_or_refresh_recap(sid)
    assert recap["text"] == ""
    assert recap["message_count"] == 0


def test_world_merges_campaign_entities(isolated_saves):
    sid = _session()
    sess = storage.get_session(sid)
    journal_storage.save_campaign("camp", {"name": "Camp", "character_ids": ["hero"]})
    storage.save_adventure(
        sess["adventure_id"],
        {"name": "Quest", "character_id": "hero", "campaign_id": "camp"},
    )
    journal_storage.save_campaign_npc("camp", "mira", {"name": "Mira", "body": "A tired scout."})
    journal_storage.save_campaign_location(
        "camp", "ford", {"name": "Old Ford", "body": "Shallow crossing."}
    )

    world = get_or_refresh_world(sid)
    names = {n["name"] for n in world["npcs"]}
    places = {n["name"] for n in world["locations"]}
    assert "Mira" in names
    assert "Old Ford" in places
    cached = storage.get_session_world_cache(sid)
    assert cached and cached["npcs"][0]["name"] == "Mira"


def test_world_extracts_marked_names_from_messages(isolated_saves):
    sid = _session()
    storage.save_session_messages(
        sid,
        [{"role": "assistant", "content": "You meet **Brannoc** beside the fire."}],
    )
    world = get_or_refresh_world(sid)
    assert any(n["name"] == "Brannoc" for n in world["npcs"])


def test_world_refresh_persists_llm_extract_without_campaign(isolated_saves):
    sid = _session()
    storage.save_session_messages(
        sid,
        [{"role": "assistant", "content": "Captain Helda waits at the quay."}],
    )
    with patch(
        "backend.dm.session_world._llm_extract",
        return_value=[
            {"kind": "npc", "name": "Helda", "body": "Harbor captain.", "source": "session"},
            {
                "kind": "location",
                "name": "The Quay",
                "body": "Salt-stained docks.",
                "source": "session",
            },
        ],
    ):
        world = get_or_refresh_world(sid, refresh=True)
    assert any(n["name"] == "Helda" for n in world["npcs"])
    assert any(n["name"] == "The Quay" for n in world["locations"])
    assert storage.get_session_world_cache(sid)["locations"][0]["name"] == "The Quay"


def test_extract_marked_names_skips_short_tokens():
    assert extract_marked_names("See **A** and **Mira Vale**.") == ["Mira Vale"]


def test_session_routes_rename_archive_recap_world(isolated_saves):
    sid = _session()
    storage.save_session_messages(
        sid,
        [{"role": "assistant", "content": "You bow to **Ilyra** in the **Moonwell**."}],
    )
    client = _client()

    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    assert listed.json()["sessions"][0]["id"] == sid

    renamed = client.patch(f"/api/sessions/{sid}", json={"name": "Moonwell night"})
    assert renamed.status_code == 200
    assert renamed.json()["session"]["name"] == "Moonwell night"

    with patch(
        "backend.dm.session_recap.generate_recap",
        return_value="You met Ilyra at the Moonwell.",
    ):
        recap = client.get(f"/api/sessions/{sid}/recap")
    assert recap.status_code == 200
    assert "Ilyra" in recap.json()["text"]

    world = client.get(f"/api/sessions/{sid}/world")
    assert world.status_code == 200
    assert any(n["name"] == "Ilyra" for n in world.json()["npcs"])

    archived = client.patch(f"/api/sessions/{sid}", json={"archived": True})
    assert archived.status_code == 200
    assert client.get("/api/sessions").json()["sessions"] == []
    hidden = client.get("/api/sessions", params={"include_archived": True})
    assert hidden.json()["sessions"][0]["archived"] is True

    client.patch(f"/api/sessions/{sid}", json={"archived": False})
    assert client.get("/api/sessions").json()["sessions"][0]["id"] == sid
