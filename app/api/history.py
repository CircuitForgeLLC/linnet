# app/api/history.py — session history endpoint
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import session_store

router = APIRouter(prefix="/session", tags=["history"])


@router.get("/{session_id}/history")
def get_history(
    session_id: str,
    min_confidence: float = 0.0,
    limit: int = 50,
) -> dict:
    """
    Return the annotation history for a session.

    min_confidence filters out low-confidence events.
    limit caps the response (most recent first).
    """
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    events = [
        e for e in session.history
        if e.confidence >= min_confidence
    ]
    events = events[-limit:]  # most recent
    return {
        "session_id": session_id,
        "count": len(events),
        "events": [
            {
                "label": e.label,
                "confidence": e.confidence,
                "speaker_id": e.speaker_id,
                "shift_magnitude": e.shift_magnitude,
                "timestamp": e.timestamp,
                "subtext": e.subtext,
                "affect": e.affect,
            }
            for e in events
        ],
    }
