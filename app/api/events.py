# app/api/events.py — SSE stream endpoint
from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.service_event import ServiceEvent
from app.models.tone_event import ToneEvent
from app.services import session_store
from app.services.translator import Translator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["events"])


@router.get("/{session_id}/stream")
async def stream_events(session_id: str, request: Request) -> StreamingResponse:
    """
    SSE stream of ToneEvent annotations for a session.

    Clients connect with EventSource:
        const es = new EventSource(`/session/${sessionId}/stream`)
        es.addEventListener('tone-event', e => { ... })

    If the session has a target_lang set, ToneEvent labels are translated via
    DeepL before emission. Labels are cached per-session — each unique label
    is translated once regardless of how often it appears.

    The stream runs until the client disconnects or the session ends.
    """
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    queue = session.subscribe()
    translator = Translator.for_session(session)

    async def generator():
        try:
            # Heartbeat comment every 15s to keep connection alive through proxies
            yield ": heartbeat\n\n"

            # If the voice probe already completed before this subscriber connected,
            # emit the result immediately rather than waiting for a queue event
            # that was already broadcast to an empty subscriber list.
            if session.voice_ready:
                yield ServiceEvent(session_id=session_id, status="ready").to_sse()
            elif session.voice_error:
                yield ServiceEvent(
                    session_id=session_id, status="error", detail=session.voice_error,
                ).to_sse()
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    # Translate tone label if a translator is configured for this session
                    if translator is not None and isinstance(event, ToneEvent):
                        translated = translator.translate(event.label)
                        if translated != event.label:
                            event = replace(event, label=translated)
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
