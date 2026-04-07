# app/services/session_store.py — session lifecycle and classifier management
from __future__ import annotations

import asyncio
import logging

from cf_voice.context import ContextClassifier

from app.models.session import Session
from app.models.tone_event import ToneEvent
from app.services.annotator import annotate

logger = logging.getLogger(__name__)

# Module-level singleton store — one per process
_sessions: dict[str, Session] = {}
_tasks: dict[str, asyncio.Task] = {}


def create_session(elcor: bool = False) -> Session:
    """Create a new session and start its ContextClassifier background task."""
    session = Session(elcor=elcor)
    _sessions[session.session_id] = session
    task = asyncio.create_task(
        _run_classifier(session),
        name=f"classifier-{session.session_id}",
    )
    _tasks[session.session_id] = task
    session.state = "running"
    logger.info("Session %s started", session.session_id)
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def active_session_count() -> int:
    """Return the number of currently running sessions."""
    return sum(1 for s in _sessions.values() if s.state == "running")


def end_session(session_id: str) -> bool:
    """Stop and remove a session. Returns True if it existed."""
    session = _sessions.pop(session_id, None)
    if session is None:
        return False
    session.state = "stopped"
    task = _tasks.pop(session_id, None)
    if task and not task.done():
        task.cancel()
    logger.info("Session %s ended", session_id)
    return True


async def _run_classifier(session: Session) -> None:
    """
    Background task: stream VoiceFrames from cf-voice and broadcast ToneEvents.

    Starts the ContextClassifier (mock or real depending on CF_VOICE_MOCK),
    converts each frame via annotator.annotate(), and fans out to subscribers.
    """
    classifier = ContextClassifier.from_env()
    try:
        async for frame in classifier.stream():
            if session.state == "stopped":
                break
            event = annotate(frame, session_id=session.session_id, elcor=session.elcor)
            if event is not None:
                session.broadcast(event)
    except asyncio.CancelledError:
        pass
    finally:
        await classifier.stop()
        session.state = "stopped"
        logger.info("Classifier stopped for session %s", session.session_id)
