# tests/test_profiles.py — DEMO_MODE and CLOUD_MODE middleware behaviour
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def demo_client():
    """TestClient with DEMO_MODE active."""
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEMO_MAX_SESSIONS"] = "2"
    # Re-import to pick up new env
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    import app.main as main_mod
    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c
    os.environ.pop("DEMO_MODE", None)
    os.environ.pop("DEMO_MAX_SESSIONS", None)
    importlib.reload(cfg)
    importlib.reload(main_mod)


@pytest.fixture()
def cloud_client():
    """TestClient with CLOUD_MODE active."""
    os.environ["CLOUD_MODE"] = "true"
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    import app.main as main_mod
    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c
    os.environ.pop("CLOUD_MODE", None)
    importlib.reload(cfg)
    importlib.reload(main_mod)


# ── Demo mode ─────────────────────────────────────────────────────────────────

def test_demo_health_mode(demo_client):
    resp = demo_client.get("/health")
    assert resp.json()["mode"] == "demo"


def test_demo_export_blocked(demo_client):
    """Export must return 403 in demo mode."""
    # Start a session first so the export route can match
    start = demo_client.post("/session/start")
    assert start.status_code == 200
    sid = start.json()["session_id"]
    resp = demo_client.get(f"/session/{sid}/export")
    assert resp.status_code == 403


def test_demo_header_present(demo_client):
    resp = demo_client.get("/health")
    assert resp.headers.get("x-linnet-mode") == "demo"


def test_demo_session_cap(demo_client):
    """Creating sessions beyond DEMO_MAX_SESSIONS returns 429."""
    # Create up to the cap
    sessions = []
    for _ in range(2):
        r = demo_client.post("/session/start")
        assert r.status_code == 200
        sessions.append(r.json()["session_id"])

    # One more should be rejected
    overflow = demo_client.post("/session/start")
    assert overflow.status_code == 429

    # Clean up
    for sid in sessions:
        demo_client.delete(f"/session/{sid}/end")


# ── Cloud mode ────────────────────────────────────────────────────────────────

def test_cloud_health_no_auth(cloud_client):
    """Health endpoint should not require auth."""
    resp = cloud_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "cloud"


def test_cloud_session_requires_auth(cloud_client):
    """Session start without X-CF-Session should be 401."""
    resp = cloud_client.post("/session/start")
    assert resp.status_code == 401


def test_cloud_session_with_auth(cloud_client):
    """Valid X-CF-Session header should pass through."""
    resp = cloud_client.post(
        "/session/start",
        headers={"X-CF-Session": "test-user-token"},
    )
    assert resp.status_code == 200


def test_cloud_header_present(cloud_client):
    resp = cloud_client.get(
        "/session/ghost",
        headers={"X-CF-Session": "user"},
    )
    assert resp.headers.get("x-linnet-mode") == "cloud"
