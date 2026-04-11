# app/models/transcript_event.py — live STT transcript event
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class TranscriptEvent:
    """
    Live transcription segment from cf-voice Whisper STT.

    Broadcasts via SSE as `event: transcript-event`. Not stored in history.
    The label field carries the raw transcript text.
    """
    session_id: str
    text: str
    speaker_id: str     # diarization label, e.g. "SPEAKER_00" or "speaker_a"
    timestamp: float

    def to_sse(self) -> str:
        payload = {
            "event_type": "transcript",
            "session_id": self.session_id,
            "text": self.text,
            "speaker_id": self.speaker_id,
            "timestamp": self.timestamp,
        }
        return f"event: transcript-event\ndata: {json.dumps(payload)}\n\n"
