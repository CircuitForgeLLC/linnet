# app/models/scene_event.py — acoustic scene and accent SSE event models
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class SceneEvent:
    """
    Acoustic scene classification from cf-voice.

    Broad scene label (e.g. "indoor_quiet", "outdoor_urban") derived from the
    AST model. Primary input to the privacy risk indicator in the frontend.
    Broadcasts via SSE as `event: scene-event`.
    Not stored in session history.
    """
    session_id: str
    label: str          # SCENE_LABELS: indoor_quiet, outdoor_urban, etc.
    confidence: float
    timestamp: float
    privacy_risk: str = "low"   # "low" | "moderate" | "high"

    def to_sse(self) -> str:
        payload = {
            "session_id": self.session_id,
            "label": self.label,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "privacy_risk": self.privacy_risk,
        }
        return f"event: scene-event\ndata: {json.dumps(payload)}\n\n"


@dataclass
class AccentEvent:
    """
    Regional accent / language identification from cf-voice.

    Gated by CF_VOICE_ACCENT=1 — only emitted when that flag is set.
    Broadcasts via SSE as `event: accent-event`.
    Not stored in session history or corrections DB.
    """
    session_id: str
    region: str         # ACCENT_LABELS: en_gb, en_us, fr, etc.
    language: str       # raw language tag from the model
    confidence: float
    timestamp: float

    def to_sse(self) -> str:
        payload = {
            "session_id": self.session_id,
            "region": self.region,
            "language": self.language,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
        return f"event: accent-event\ndata: {json.dumps(payload)}\n\n"
