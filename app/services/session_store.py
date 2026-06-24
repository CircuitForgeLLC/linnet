# app/services/session_store.py — session lifecycle and classifier management
from __future__ import annotations

import asyncio
import logging
import time

from app.config import settings
from app.models.service_event import ServiceEvent
from app.models.session import Session
from app.models.tone_event import ToneEvent
from app.services.annotator import annotate

logger = logging.getLogger(__name__)

# Module-level singleton store — one per process
_sessions: dict[str, Session] = {}
_tasks: dict[str, asyncio.Task] = {}
_reaper_task: asyncio.Task | None = None

# Audio accumulation buffer per session.
# We accumulate 100ms PCM chunks until we have CLASSIFY_WINDOW_MS of audio,
# then fire a single /classify call. Real emotion models need ≥500ms context.
_CLASSIFY_WINDOW_MS = 1000         # ms of audio per classify call; wav2vec2 needs ≥1s context
_CHUNK_MS = 100                     # AudioWorklet sends 1600 samples @ 16kHz = 100ms
_CHUNKS_PER_WINDOW = _CLASSIFY_WINDOW_MS // _CHUNK_MS   # 10 chunks
_audio_buffers: dict[str, list[bytes]] = {}


async def create_session(
    elcor: bool = False,
    tier: str = "free",
    user_id: str = "",
    target_lang: str = "",
    byok_deepl_key: str = "",
    window_ms: int = 1000,
    transcribe_lang: str = "",
    num_speakers: int = 0,
) -> Session:
    """Create a new session and start its ContextClassifier background task.

    If CF_ORCH_URL is configured, requests a managed cf-voice instance before
    starting the classifier. Falls back to in-process mock if allocation fails.
    """
    session = Session(
        elcor=elcor,
        tier=tier,
        user_id=user_id,
        target_lang=target_lang,
        byok_deepl_key=byok_deepl_key,
        window_ms=window_ms,
        transcribe_lang=transcribe_lang,
        num_speakers=num_speakers,
    )
    _sessions[session.session_id] = session
    await _allocate_voice(session)
    task = asyncio.create_task(
        _run_classifier(session),
        name=f"classifier-{session.session_id}",
    )
    _tasks[session.session_id] = task
    asyncio.create_task(
        _probe_voice_ready(session),
        name=f"voice-ready-{session.session_id}",
    )
    session.state = "running"
    logger.info(
        "Session %s started (voice=%s)",
        session.session_id,
        session.cf_voice_url or "in-process",
    )
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)


def active_session_count() -> int:
    """Return the number of currently running sessions."""
    return sum(1 for s in _sessions.values() if s.state == "running")


async def end_session(session_id: str) -> bool:
    """Stop and remove a session. Returns True if it existed.

    For Paid tier sessions with annotation history, saves a snapshot to SQLite
    so the user can resume the session later.
    """
    session = _sessions.pop(session_id, None)
    if session is None:
        return False
    session.state = "stopped"
    task = _tasks.pop(session_id, None)
    if task and not task.done():
        task.cancel()
    _audio_buffers.pop(session_id, None)
    await _release_voice(session)

    if session.tier in ("paid", "premium") and session.history:
        _save_snapshot(session)

    logger.info("Session %s ended", session_id)
    return True


def _save_snapshot(session: Session) -> None:
    """Persist a session's annotation history to the snapshots table."""
    import json
    import time as _time
    import uuid

    try:
        from app.db import get_connection
        conn = get_connection()
        snapshot_id = str(uuid.uuid4())
        events_json = json.dumps([
            {
                "label": e.label,
                "confidence": e.confidence,
                "speaker_id": e.speaker_id,
                "shift_magnitude": e.shift_magnitude,
                "timestamp": e.timestamp,
                "subtext": e.subtext,
                "affect": e.affect,
            }
            for e in session.history
        ])
        conn.execute(
            """
            INSERT INTO session_snapshots
                (id, user_id, session_id, created_at, ended_at, elcor, event_count, events_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                session.user_id,
                session.session_id,
                session.created_at,
                _time.time(),
                1 if session.elcor else 0,
                len(session.history),
                events_json,
            ),
        )
        conn.commit()
        conn.close()
        logger.info(
            "Snapshot %s saved for session %s (%d events)",
            snapshot_id, session.session_id, len(session.history),
        )
    except Exception as exc:
        logger.warning("Failed to save snapshot for session %s: %s", session.session_id, exc)


async def _probe_voice_ready(session: Session) -> None:
    """Poll the cf-voice health endpoint and broadcast a service-event when ready.

    Retries every second for up to 30s. On success, broadcasts status="ready"
    so the frontend can unlock the mic button. On timeout, broadcasts
    status="error" so the UI can surface a warning.

    No-op for in-process mode (no cf_voice_url) — broadcasts ready immediately.
    """
    def _mark_ready() -> None:
        session.voice_ready = True
        session.broadcast(ServiceEvent(session_id=session.session_id, status="ready"))

    def _mark_error(detail: str) -> None:
        session.voice_error = detail
        session.broadcast(ServiceEvent(
            session_id=session.session_id, status="error", detail=detail,
        ))

    if not session.cf_voice_url:
        # In-process mock or no managed voice: ready immediately
        _mark_ready()
        return

    asyncio.create_task(
        _poll_model_status(session),
        name=f"model-status-{session.session_id}",
    )

    import httpx

    health_url = session.cf_voice_url.rstrip("/") + "/health"
    deadline = time.monotonic() + 30.0

    while time.monotonic() < deadline:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(health_url)
            if resp.status_code == 200:
                _mark_ready()
                logger.debug("cf-voice ready for session %s", session.session_id)
                # Surface any soft warnings (e.g. diarize configured but HF_TOKEN missing)
                try:
                    data = resp.json()
                    for msg in data.get("warnings", []):
                        session.broadcast(ServiceEvent(
                            session_id=session.session_id,
                            status="warning",
                            detail=msg,
                        ))
                except Exception:
                    pass
                return
        except Exception:
            pass
        await asyncio.sleep(1.0)

    _mark_error("Voice service did not become ready in time. Try reloading.")
    logger.warning("cf-voice readiness probe timed out for session %s", session.session_id)


_MODEL_LABELS = {
    "stt":        "speech-to-text (Whisper)",
    "diarizer":   "speaker diarization (pyannote)",
    "dimensional": "emotion dimensions (audeering)",
    "prosody":    "prosody (openSMILE)",
}


async def _poll_model_status(session: Session) -> None:
    """Poll cf-voice /health for per-model download progress and broadcast
    loading/ready events to the frontend. Stops when all models are stable."""
    if not session.cf_voice_url:
        return

    import httpx

    health_url = session.cf_voice_url.rstrip("/") + "/health"
    prev: dict[str, str] = {}

    # Poll for up to 10 minutes (large model downloads can take a while)
    deadline = time.monotonic() + 600.0

    while time.monotonic() < deadline and session.state == "running":
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(health_url)
            if resp.status_code == 200:
                data = resp.json()
                models: dict[str, str] = data.get("models", {})

                for key, status in models.items():
                    if models.get(key) == prev.get(key):
                        continue
                    label = _MODEL_LABELS.get(key, key)
                    if status == "loading":
                        session.broadcast(ServiceEvent(
                            session_id=session.session_id,
                            status="loading",
                            detail=f"Downloading {label}…",
                        ))
                    elif status == "ready" and prev.get(key) == "loading":
                        session.broadcast(ServiceEvent(
                            session_id=session.session_id,
                            status="loading",
                            detail=f"{label.capitalize()} ready.",
                        ))
                    elif status == "error":
                        session.broadcast(ServiceEvent(
                            session_id=session.session_id,
                            status="warning",
                            detail=f"Failed to load {label}.",
                        ))

                prev = dict(models)

                # Done when nothing is still loading
                if models and all(s != "loading" for s in models.values()):
                    # Clear any loading detail
                    session.broadcast(ServiceEvent(
                        session_id=session.session_id,
                        status="loading",
                        detail="",
                    ))
                    return
        except Exception:
            pass

        await asyncio.sleep(2.0)


async def _allocate_voice(session: Session) -> None:
    """Request a managed cf-voice instance from cf-orch. No-op if CF_ORCH_URL is unset."""
    # Static override takes precedence — skip cf-orch allocation
    if settings.cf_voice_url:
        session.cf_voice_url = settings.cf_voice_url
        return
    if not settings.cf_orch_url:
        return

    import httpx

    url = settings.cf_orch_url.rstrip("/") + "/api/services/cf-voice/allocate"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"caller": "linnet", "ttl_s": 3600.0})
            resp.raise_for_status()
            data = resp.json()
        session.cf_voice_url = data["url"]
        session.cf_voice_allocation_id = data["allocation_id"]
        logger.info(
            "cf-orch allocated cf-voice for session %s: %s (alloc=%s)",
            session.session_id, data["url"], data["allocation_id"],
        )
    except Exception as exc:
        logger.warning(
            "cf-orch allocation failed for session %s: %s — falling back to in-process",
            session.session_id, exc,
        )


async def _release_voice(session: Session) -> None:
    """Release a cf-voice allocation back to cf-orch. No-op if not orch-managed."""
    if not session.cf_voice_allocation_id or not settings.cf_orch_url:
        return

    import httpx

    url = (
        settings.cf_orch_url.rstrip("/")
        + f"/api/services/cf-voice/allocations/{session.cf_voice_allocation_id}"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(url)
        logger.info("Released cf-voice allocation for session %s", session.session_id)
    except Exception as exc:
        logger.warning(
            "cf-orch release failed for session %s: %s", session.session_id, exc
        )


async def _run_classifier(session: Session) -> None:
    """
    Background task: stream VoiceFrames and broadcast ToneEvents.

    Two modes:
    - Sidecar (cf-orch allocated or CF_VOICE_URL set): holds the session open
      while audio chunks are forwarded to cf-voice via forward_audio_chunk().
    - In-process (no sidecar): runs ContextClassifier.from_env() directly.
      Used for local dev and mock mode when CF_ORCH_URL is unset or allocation failed.
    """
    if session.cf_voice_url:
        await _run_classifier_sidecar(session)
    else:
        await _run_classifier_inprocess(session)


async def _run_classifier_inprocess(session: Session) -> None:
    """In-process path: ContextClassifier.stream() — used when CF_VOICE_URL is unset."""
    from cf_voice.context import ContextClassifier

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


async def _run_classifier_sidecar(session: Session) -> None:
    """
    Sidecar path: wait for audio chunks forwarded via forward_audio_chunk().

    The sidecar does not self-generate frames — audio arrives from the browser
    WebSocket and is sent to cf-voice /classify. This task holds the session
    open and handles cleanup.
    """
    try:
        while session.state == "running":
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass
    finally:
        session.state = "stopped"
        logger.info("Sidecar session ended for session %s", session.session_id)


async def forward_audio_chunk(
    session: Session,
    audio_b64: str,
    timestamp: float,
) -> None:
    """
    Accumulate PCM chunks into 500ms windows, then forward to cf-voice /classify.

    The AudioWorklet sends 100ms chunks; we buffer 10 of them (_CHUNKS_PER_WINDOW)
    before firing a classify call. This gives wav2vec2 a full second of context
    and keeps the classify rate at 1/s instead of 10/s.

    No-op when no cf-voice sidecar is allocated (in-process path handles its own input).
    """
    voice_url = session.cf_voice_url
    if not voice_url:
        return

    import base64 as _b64
    import httpx

    from app.models.speaker_event import SpeakerEvent
    from cf_voice.models import VoiceFrame

    # Decode incoming chunk and append to per-session buffer
    raw = _b64.b64decode(audio_b64)
    buf = _audio_buffers.setdefault(session.session_id, [])
    buf.append(raw)

    chunks_needed = max(1, session.window_ms // _CHUNK_MS)
    if len(buf) < chunks_needed:
        return  # not enough audio yet — wait for more chunks

    # Flush: concatenate window, reset buffer
    window_bytes = b"".join(buf)
    buf.clear()
    window_b64 = _b64.b64encode(window_bytes).decode()

    url = voice_url.rstrip("/") + "/classify"
    payload = {
        "audio_chunk": window_b64,
        "timestamp": timestamp,
        "elcor": session.elcor,
        "session_id": session.session_id,
        "language": session.transcribe_lang or None,  # None = Whisper auto-detect
        "num_speakers": session.num_speakers or None,  # None = pyannote auto-detect
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("cf-voice sidecar call failed for session %s: %s", session.session_id, exc)
        return

    from app.models.queue_event import QueueEvent
    from app.models.transcript_event import TranscriptEvent
    from app.models.scene_event import SceneEvent, AccentEvent

    for ev in data.get("events", []):
        etype = ev.get("event_type")

        if etype == "tone":
            frame = VoiceFrame(
                label=ev["label"],
                confidence=ev["confidence"],
                speaker_id=ev.get("speaker_id", ""),
                shift_magnitude=ev.get("shift_magnitude", 0.0),
                timestamp=ev["timestamp"],
            )
            tone = annotate(frame, session_id=session.session_id, elcor=session.elcor)
            if tone is not None:
                session.broadcast(tone)

        elif etype == "speaker":
            speaker = SpeakerEvent(
                session_id=session.session_id,
                label=ev["label"],
                confidence=ev.get("confidence", 1.0),
                timestamp=ev["timestamp"],
            )
            session.broadcast(speaker)

        elif etype == "transcript":
            transcript = TranscriptEvent(
                session_id=session.session_id,
                text=ev["label"],
                speaker_id=ev.get("speaker_id", "speaker_a"),
                timestamp=ev["timestamp"],
            )
            session.broadcast(transcript)

        elif etype in ("queue", "environ"):
            queue_ev = QueueEvent(
                session_id=session.session_id,
                event_type=etype,
                label=ev["label"],
                confidence=ev.get("confidence", 1.0),
                timestamp=ev["timestamp"],
            )
            session.broadcast(queue_ev)

        elif etype == "scene":
            scene_ev = SceneEvent(
                session_id=session.session_id,
                label=ev["label"],
                confidence=ev.get("confidence", 1.0),
                timestamp=ev["timestamp"],
                privacy_risk=ev.get("privacy_risk", "low"),
            )
            session.broadcast(scene_ev)

        elif etype == "accent":
            accent_ev = AccentEvent(
                session_id=session.session_id,
                region=ev["label"],
                language=ev.get("language", ""),
                confidence=ev.get("confidence", 1.0),
                timestamp=ev["timestamp"],
            )
            session.broadcast(accent_ev)


# ── Idle session reaper ───────────────────────────────────────────────────────

def _should_reap(session: Session, now: float) -> bool:
    """
    Return True if a session should be reaped.

    Free tier: reap when last subscriber left > SESSION_IDLE_TTL_S ago.
    Paid/premium: reap when last activity (broadcast) > SESSION_PAID_TTL_S ago,
    regardless of subscriber state. This lets paid sessions survive reconnects
    but enforces a hard 30-min activity timeout.
    """
    if session.state != "running":
        return False

    if session.tier in ("paid", "premium"):
        return (now - session.last_activity_at) > settings.session_paid_ttl_s

    # Free tier: only reap when there are no subscribers and the idle clock is running
    return (
        session.subscriber_count() == 0
        and session.last_subscriber_left_at is not None
        and (now - session.last_subscriber_left_at) > settings.session_idle_ttl_s
    )


async def _reaper_loop() -> None:
    """
    Periodically kill sessions that have exceeded their tier TTL.

    Free tier (90s): reaps when last SSE subscriber left > 90s ago.
      Covers mobile tab timeout / screen lock / crash.

    Paid tier (30 min): reaps when last annotation event > 30 min ago,
      regardless of subscriber state. Allows paid users to reconnect within
      the window without losing their session.

    The reaper runs every REAP_INTERVAL_S seconds (half the free TTL, capped
    at 60s, so worst-case overshoot is small).
    """
    ttl = settings.session_idle_ttl_s
    interval = max(15, min(60, ttl // 2))
    logger.info("Session reaper started (free TTL=%ds, paid TTL=%ds, check every %ds)",
                ttl, settings.session_paid_ttl_s, interval)
    while True:
        await asyncio.sleep(interval)
        now = time.monotonic()
        to_reap = [sid for sid, s in list(_sessions.items()) if _should_reap(s, now)]
        for sid in to_reap:
            session = _sessions.get(sid)
            tier = session.tier if session else "free"
            logger.info("Reaping idle %s session %s", tier, sid)
            await end_session(sid)


async def _reaper_loop_once() -> None:
    """Single reaper pass — used by tests to avoid sleeping."""
    now = time.monotonic()
    to_reap = [sid for sid, s in list(_sessions.items()) if _should_reap(s, now)]
    for sid in to_reap:
        session = _sessions.get(sid)
        tier = session.tier if session else "free"
        logger.info("Reaping idle %s session %s", tier, sid)
        await end_session(sid)


def start_reaper() -> None:
    """Start the idle session reaper background task. Called from app lifespan."""
    global _reaper_task
    if _reaper_task is None or _reaper_task.done():
        _reaper_task = asyncio.create_task(_reaper_loop(), name="session-reaper")


async def stop_reaper() -> None:
    """Cancel the reaper task cleanly. Called from app lifespan shutdown."""
    global _reaper_task
    if _reaper_task and not _reaper_task.done():
        _reaper_task.cancel()
        try:
            await _reaper_task
        except asyncio.CancelledError:
            pass
    _reaper_task = None
