# app/models/queue_event.py — call queue state and environment events
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class QueueEvent:
    """
    Call queue state or environmental classification from cf-voice AST.

    event_type is either "queue" or "environ".
    Broadcasts via SSE as `event: queue-event` or `event: environ-event`.
    Not stored in session history.
    """
    session_id: str
    event_type: str     # "queue" or "environ"
    label: str          # e.g. "hold_music", "ringback", "call_center", "quiet"
    confidence: float
    timestamp: float

    def to_sse(self) -> str:
        payload = {
            "event_type": self.event_type,
            "session_id": self.session_id,
            "label": self.label,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
        sse_name = "queue-event" if self.event_type == "queue" else "environ-event"
        return f"event: {sse_name}\ndata: {json.dumps(payload)}\n\n"
