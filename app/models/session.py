# app/models/session.py — Session dataclass
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from app.models.tone_event import ToneEvent

SessionState = Literal["starting", "running", "stopped"]


@runtime_checkable
class SessionEvent(Protocol):
    """Any event that can be broadcast over SSE from a session."""
    def to_sse(self) -> str: ...


@dataclass
class Session:
    """
    An active annotation session.

    The session owns the subscriber queue fan-out: each SSE connection
    subscribes by calling subscribe() and gets its own asyncio.Queue.
    The session_store fans out ToneEvents to all queues via broadcast().
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    state: SessionState = "starting"
    created_at: float = field(default_factory=time.monotonic)
    elcor: bool = False

    # cf-voice sidecar — populated by session_store._allocate_voice() when cf-orch
    # is configured. Empty string means in-process fallback is active.
    cf_voice_url: str = ""
    cf_voice_allocation_id: str = ""

    # History: last 50 events retained for GET /session/{id}/history
    history: list[ToneEvent] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list, repr=False)

    # Idle tracking: monotonic timestamp of when the last subscriber left.
    # None means at least one subscriber is currently active, or the session
    # has never had one yet (just started). The reaper uses this to detect
    # abandoned sessions after a mobile tab timeout.
    last_subscriber_left_at: float | None = field(default=None, repr=False)

    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue:
        """Add an SSE subscriber. Returns its dedicated queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        # Reset idle clock — someone is watching again
        self.last_subscriber_left_at = None
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass
        # Start the idle clock when the last subscriber leaves
        if not self._subscribers:
            self.last_subscriber_left_at = time.monotonic()

    def broadcast(self, event: SessionEvent) -> None:
        """Fan out any SessionEvent (tone, speaker, etc.) to all SSE subscribers."""
        if isinstance(event, ToneEvent):
            if len(self.history) >= 50:
                self.history.pop(0)
            self.history.append(event)

        dead: list[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)
