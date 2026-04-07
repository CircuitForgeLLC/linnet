# tests/conftest.py
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force mock mode so tests never touch real inference
os.environ.setdefault("CF_VOICE_MOCK", "1")

from app.main import app  # noqa: E402 — must come after env setup


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session_id(client: TestClient) -> str:
    """Create a session and return its ID."""
    resp = client.post("/session/start")
    assert resp.status_code == 200
    return resp.json()["session_id"]
