# app/models/session.py — Session dataclass
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.models.tone_event import ToneEvent

SessionState = Literal["starting", "running", "stopped"]


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

    # History: last 50 events retained for GET /session/{id}/history
    history: list[ToneEvent] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def subscribe(self) -> asyncio.Queue:
        """Add an SSE subscriber. Returns its dedicated queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def broadcast(self, event: ToneEvent) -> None:
        """Fan out a ToneEvent to all current SSE subscribers."""
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
