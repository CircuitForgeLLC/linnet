# app/api/events.py — SSE stream endpoint
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["events"])


@router.get("/{session_id}/stream")
async def stream_events(session_id: str, request: Request) -> StreamingResponse:
    """
    SSE stream of ToneEvent annotations for a session.

    Clients connect with EventSource:
        const es = new EventSource(`/session/${sessionId}/stream`)
        es.addEventListener('tone-event', e => { ... })

    The stream runs until the client disconnects or the session ends.
    """
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    queue = session.subscribe()

    async def generator():
        try:
            # Heartbeat comment every 15s to keep connection alive through proxies
            yield ": heartbeat\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            session.unsubscribe(queue)
            logger.debug("SSE subscriber disconnected from session %s", session_id)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )
