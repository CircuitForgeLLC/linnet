# app/api/audio.py — WebSocket audio ingestion endpoint
#
# Receives raw PCM Int16 audio chunks from the browser's AudioWorkletProcessor.
# Each message is a binary frame: 16kHz mono Int16 PCM.
# The backend accumulates chunks until cf-voice processes them.
#
# Notation v0.1.x: audio is accepted and acknowledged but inference runs
# through the background ContextClassifier (started at session creation),
# not inline here. This endpoint is wired for the real audio path
# (Navigation v0.2.x) where chunks feed the STT + diarizer directly.
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["audio"])


@router.websocket("/{session_id}/audio")
async def audio_ws(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for binary PCM audio upload.

    Clients (browser AudioWorkletProcessor) send binary frames.
    Server acknowledges each frame with {"ok": true}.

    In mock mode (CF_VOICE_MOCK=1) the session's ContextClassifier generates
    synthetic frames independently -- audio sent here is accepted but not
    processed. Real inference wiring happens in Navigation v0.2.x.
    """
    session = session_store.get_session(session_id)
    if session is None:
        await websocket.close(code=4004, reason=f"Session {session_id} not found")
        return

    await websocket.accept()
    logger.info("Audio WS connected for session %s", session_id)

    try:
        while True:
            data = await websocket.receive_bytes()
            # Notation v0.1.x: acknowledge receipt; real inference in v0.2.x
            await websocket.send_json({"ok": True, "bytes": len(data)})
    except WebSocketDisconnect:
        logger.info("Audio WS disconnected for session %s", session_id)
