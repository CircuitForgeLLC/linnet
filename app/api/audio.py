# app/api/audio.py — WebSocket audio ingestion endpoint
#
# Receives raw PCM Int16 audio chunks from the browser's AudioWorkletProcessor.
# Each message is a binary frame: 16kHz mono Int16 PCM.
#
# When CF_VOICE_URL is set (cf-voice sidecar allocated by cf-orch), each chunk
# is base64-encoded and forwarded to cf-voice /classify. The resulting tone
# events are broadcast to SSE subscribers via the session store.
#
# When CF_VOICE_URL is unset (local dev / mock mode), chunks are acknowledged
# but not forwarded — the in-process ContextClassifier.stream() generates
# synthetic frames independently.
from __future__ import annotations

import base64
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["audio"])

_SESSION_START: dict[str, float] = {}


@router.websocket("/{session_id}/audio")
async def audio_ws(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for binary PCM audio upload.

    Clients (browser AudioWorkletProcessor) send binary Int16 frames.
    Server acknowledges each frame with {"ok": true, "bytes": N}.

    When CF_VOICE_URL is configured, each chunk is forwarded to the cf-voice
    sidecar and the resulting tone events are broadcast to SSE subscribers.
    """
    session = session_store.get_session(session_id)
    if session is None:
        await websocket.close(code=4004, reason=f"Session {session_id} not found")
        return

    await websocket.accept()
    _SESSION_START[session_id] = time.monotonic()
    logger.info("Audio WS connected for session %s", session_id)

    try:
        while True:
            data = await websocket.receive_bytes()
            timestamp = time.monotonic() - _SESSION_START.get(session_id, 0.0)
            await websocket.send_json({"ok": True, "bytes": len(data)})
            # Forward to cf-voice sidecar (no-op if CF_VOICE_URL is unset)
            audio_b64 = base64.b64encode(data).decode()
            await session_store.forward_audio_chunk(session, audio_b64, timestamp)
    except WebSocketDisconnect:
        logger.info("Audio WS disconnected for session %s", session_id)
        _SESSION_START.pop(session_id, None)
