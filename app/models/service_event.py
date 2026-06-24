# app/models/service_event.py — system/service lifecycle events for the SSE stream
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class ServiceEvent:
    """
    Lifecycle signal broadcast over SSE to frontend subscribers.

    Currently used to signal when the cf-voice backend is ready to accept audio.
    The frontend holds the mic button in a disabled "loading" state until it
    receives status="ready".

    SSE event name: service-event
    """
    session_id: str
    status: str       # "ready" | "loading" | "error"
    detail: str = ""  # human-readable message shown in the UI

    def to_sse(self) -> str:
        payload = {
            "event_type": "service",
            "session_id": self.session_id,
            "status": self.status,
            "detail": self.detail,
        }
        return f"event: service-event\ndata: {json.dumps(payload)}\n\n"
