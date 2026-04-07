# tests/test_session_lifecycle.py — session CRUD + history/export endpoints
from __future__ import annotations


def test_start_session(client):
    resp = client.post("/session/start")
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert body["state"] == "running"
    assert body["elcor"] is False


def test_start_session_elcor(client):
    resp = client.post("/session/start", json={"elcor": True})
    assert resp.status_code == 200
    assert resp.json()["elcor"] is True


def test_get_session(client, session_id):
    resp = client.get(f"/session/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


def test_get_session_not_found(client):
    resp = client.get("/session/no-such-session")
    assert resp.status_code == 404


def test_end_session(client, session_id):
    resp = client.delete(f"/session/{session_id}/end")
    assert resp.status_code == 200
    assert resp.json()["state"] == "stopped"


def test_end_session_not_found(client):
    resp = client.delete("/session/ghost/end")
    assert resp.status_code == 404


def test_history_empty(client, session_id):
    resp = client.get(f"/session/{session_id}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["events"] == []


def test_history_not_found(client):
    resp = client.get("/session/ghost/history")
    assert resp.status_code == 404


def test_export_empty(client, session_id):
    resp = client.get(f"/session/{session_id}/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert "attachment" in resp.headers["content-disposition"]
    import json
    body = json.loads(resp.content)
    assert body["session_id"] == session_id
    assert body["events"] == []


def test_export_not_found(client):
    resp = client.get("/session/ghost/export")
    assert resp.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
