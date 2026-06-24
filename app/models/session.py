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

    # Tier and user identity — set at creation from the license/auth resolution.
    # Used by the reaper for tier-aware TTL and by snapshot logic for user scoping.
    tier: str = "free"
    user_id: str = ""  # cf_user in cloud mode; empty string for self-hosted

    # cf-voice sidecar — populated by session_store._allocate_voice() when cf-orch
    # is configured. Empty string means in-process fallback is active.
    cf_voice_url: str = ""
    cf_voice_allocation_id: str = ""

    # Translation settings — set at session start from StartRequest.
    # target_lang: BCP-47 tag (e.g. "es", "fr", "de") or empty string = no translation.
    # byok_deepl_key: user-supplied DeepL Free API key; bypasses Paid gate for translation.
    target_lang: str = ""
    byok_deepl_key: str = ""

    # Audio classification settings — set at session start, cannot be changed mid-session.
    # window_ms: how many ms of PCM to accumulate before calling cf-voice /classify.
    #   AudioWorklet sends 100ms chunks; must be a multiple of 100. Default 1000ms.
    # transcribe_lang: BCP-47 language hint for Whisper (e.g. "en", "es").
    #   Empty = Whisper auto-detects (slower, less accurate on short clips).
    # num_speakers: hint for pyannote diarization. 0 = auto-detect; 1–8 = fixed count
    #   passed as min_speakers=max_speakers. Auto is slower; fixed count improves accuracy.
    window_ms: int = 1000
    transcribe_lang: str = ""
    num_speakers: int = 0

    # History: last 200 events retained for GET /session/{id}/history and snapshots.
    history: list[ToneEvent] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list, repr=False)

    # Voice readiness: set by _probe_voice_ready() once cf-voice health check passes.
    # Used to immediately send a service-event to late SSE subscribers who connect
    # after the probe has already completed (avoids the broadcast-before-subscribe race).
    voice_ready: bool = False
    voice_error: str = ""  # non-empty when probe timed out

    # Activity tracking: updated on every broadcast() so the paid-tier reaper
    # can measure 30-min hard idle (activity-based, not subscriber-based).
    last_activity_at: float = field(default_factory=time.monotonic, repr=False)

    # Idle tracking: monotonic timestamp of when the last subscriber left.
    # None means at least one subscriber is currently active, or the session
    # has never had one yet (just started). The free-tier reaper uses this to
    # detect abandoned sessions after a mobile tab timeout.
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
        self.last_activity_at = time.monotonic()

        if isinstance(event, ToneEvent):
            if len(self.history) >= 200:
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
