# app/api/export.py — session export endpoint (Navigation v0.2.x)
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services import session_store

router = APIRouter(prefix="/session", tags=["export"])


@router.get("/{session_id}/export")
def export_session(session_id: str) -> Response:
    """
    Export the full session annotation log as JSON.

    Returns a downloadable JSON file with all ToneEvents and session metadata.
    All data is local — nothing is sent to any server.
    """
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    payload = {
        "session_id": session.session_id,
        "elcor": session.elcor,
        "events": [
            {
                "label": e.label,
                "confidence": e.confidence,
                "speaker_id": e.speaker_id,
                "shift_magnitude": e.shift_magnitude,
                "timestamp": e.timestamp,
                "subtext": e.subtext,
                "affect": e.affect,
                "shift_direction": e.shift_direction,
            }
            for e in session.history
        ],
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="linnet-session-{session_id}.json"'
        },
    )
