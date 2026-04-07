# app/models/tone_event.py — Linnet's internal ToneEvent model
#
# Wraps cf_voice.events.ToneEvent for SSE serialisation.
# The wire format (JSON field names) is locked per cf-core#40.
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from cf_voice.events import ToneEvent as VoiceToneEvent
from cf_voice.events import tone_event_from_voice_frame
from cf_voice.models import VoiceFrame


@dataclass
class ToneEvent:
    """
    Linnet's session-scoped ToneEvent — ready for SSE serialisation.

    Extends cf_voice.events.ToneEvent with session_id and serialisation helpers.
    Field names are the stable SSE wire format (cf-core#40).
    """
    label: str
    confidence: float
    speaker_id: str
    shift_magnitude: float
    timestamp: float
    session_id: str
    subtext: str | None = None
    affect: str = "neutral"
    shift_direction: str = "stable"
    prosody_flags: list[str] = field(default_factory=list)
    elcor: bool = False

    @classmethod
    def from_voice_frame(
        cls,
        frame: VoiceFrame,
        session_id: str,
        elcor: bool = False,
    ) -> "ToneEvent":
        """Convert a cf_voice VoiceFrame into a session-scoped ToneEvent."""
        voice_event = tone_event_from_voice_frame(
            frame_label=frame.label,
            frame_confidence=frame.confidence,
            shift_magnitude=frame.shift_magnitude,
            timestamp=frame.timestamp,
            elcor=elcor,
        )
        return cls(
            label=frame.label,
            confidence=frame.confidence,
            speaker_id=frame.speaker_id,
            shift_magnitude=frame.shift_magnitude,
            timestamp=frame.timestamp,
            session_id=session_id,
            subtext=voice_event.subtext,
            affect=voice_event.affect,
            shift_direction=voice_event.shift_direction,
            prosody_flags=voice_event.prosody_flags,
            elcor=elcor,
        )

    def to_sse(self) -> str:
        """
        Serialise to SSE wire format.

        Returns the full SSE message string including event type, data,
        and trailing blank line:
            event: tone-event\ndata: {...}\n\n
        """
        payload = {
            "event_type": "tone",
            "label": self.label,
            "confidence": self.confidence,
            "speaker_id": self.speaker_id,
            "shift_magnitude": self.shift_magnitude,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "subtext": self.subtext,
            "affect": self.affect,
            "shift_direction": self.shift_direction,
            "prosody_flags": self.prosody_flags,
        }
        return f"event: tone-event\ndata: {json.dumps(payload)}\n\n"

    def is_reliable(self, threshold: float = 0.6) -> bool:
        return self.confidence >= threshold
