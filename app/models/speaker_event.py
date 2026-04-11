# app/models/speaker_event.py — speaker classification event
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class SpeakerEvent:
    """
    Speaker/environment classification from cf-voice.

    Broadcasts via SSE as `event: speaker-event` alongside tone-events.
    Not stored in session history (tone history only).
    """
    session_id: str
    label: str          # e.g. "human", "no_speaker", "ivr_synth"
    confidence: float
    timestamp: float

    def to_sse(self) -> str:
        payload = {
            "event_type": "speaker",
            "session_id": self.session_id,
            "label": self.label,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
        return f"event: speaker-event\ndata: {json.dumps(payload)}\n\n"
