# tests/test_reaper.py — idle session reaper and subscriber idle tracking
from __future__ import annotations

import asyncio
import time

import pytest

from app.models.session import Session
from app.services import session_store


@pytest.fixture(autouse=True)
def clean_sessions():
    """Ensure the session store is empty before and after each test."""
    session_store._sessions.clear()
    session_store._tasks.clear()
    session_store._audio_buffers.clear()
    yield
    session_store._sessions.clear()
    session_store._tasks.clear()
    session_store._audio_buffers.clear()


# ── Session model: subscriber idle tracking ───────────────────────────────────

def test_last_subscriber_left_at_none_on_start():
    s = Session()
    assert s.last_subscriber_left_at is None


def test_last_subscriber_left_at_set_on_unsubscribe():
    s = Session()
    q = s.subscribe()
    assert s.last_subscriber_left_at is None  # someone is watching
    s.unsubscribe(q)
    assert s.last_subscriber_left_at is not None


def test_last_subscriber_left_at_cleared_on_resubscribe():
    s = Session()
    q = s.subscribe()
    s.unsubscribe(q)
    assert s.last_subscriber_left_at is not None
    # New subscriber arrives — idle clock resets
    q2 = s.subscribe()
    assert s.last_subscriber_left_at is None
    s.unsubscribe(q2)


def test_subscriber_count():
    s = Session()
    assert s.subscriber_count() == 0
    q1 = s.subscribe()
    q2 = s.subscribe()
    assert s.subscriber_count() == 2
    s.unsubscribe(q1)
    assert s.subscriber_count() == 1
    s.unsubscribe(q2)
    assert s.subscriber_count() == 0


# ── Reaper logic ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reaper_kills_idle_session(monkeypatch):
    """
    A session with no subscribers for longer than the TTL should be reaped.
    We monkeypatch SESSION_IDLE_TTL_S to 0 and manually invoke _reaper_loop
    for a single cycle.
    """
    monkeypatch.setattr(session_store.settings, "session_idle_ttl_s", 0)

    session = await session_store.create_session()
    sid = session.session_id

    # Simulate a subscriber connecting then leaving
    q = session.subscribe()
    session.unsubscribe(q)

    # Force last_subscriber_left_at into the past
    session.last_subscriber_left_at = time.monotonic() - 1.0

    assert sid in session_store._sessions

    # Run one reaper cycle directly
    await session_store._reaper_loop_once()

    assert sid not in session_store._sessions


@pytest.mark.asyncio
async def test_reaper_spares_session_with_active_subscriber(monkeypatch):
    """A session that still has an active SSE subscriber must not be reaped."""
    monkeypatch.setattr(session_store.settings, "session_idle_ttl_s", 0)

    session = await session_store.create_session()
    sid = session.session_id

    # Subscriber is still connected — idle clock is None
    _q = session.subscribe()
    assert session.last_subscriber_left_at is None

    await session_store._reaper_loop_once()

    assert sid in session_store._sessions
    session.unsubscribe(_q)


@pytest.mark.asyncio
async def test_reaper_spares_session_within_ttl(monkeypatch):
    """A session that lost its subscriber recently (within TTL) must survive."""
    monkeypatch.setattr(session_store.settings, "session_idle_ttl_s", 3600)

    session = await session_store.create_session()
    sid = session.session_id

    q = session.subscribe()
    session.unsubscribe(q)
    # last_subscriber_left_at is just now — well within TTL

    await session_store._reaper_loop_once()

    assert sid in session_store._sessions
