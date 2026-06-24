# app/api/sessions.py — session lifecycle endpoints
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import tiers
from app.config import settings
from app.services import session_store

router = APIRouter(prefix="/session", tags=["sessions"])


class StartRequest(BaseModel):
    elcor: bool = False   # enable Elcor subtext format (easter egg)
    # Self-hosted installs may pass their license key per-request instead of via env var.
    # Cloud mode ignores this field — tier is resolved from the authenticated user_id.
    license_key: str | None = None
    # Translation: BCP-47 target language tag (e.g. "es", "fr", "de").
    # Empty string or omitted = no translation.
    target_lang: str = ""
    # BYOK DeepL API key — user's own DeepL Free key.
    # Bypasses the Paid tier gate for translation only (see tiers.py BYOK_UNLOCKABLE).
    byok_deepl_key: str = ""
    # Audio classification tuning.
    # window_ms: PCM accumulation window before each /classify call (multiple of 100).
    #   Longer = more Whisper context = better accuracy, higher latency. Default 1000ms.
    # transcribe_lang: BCP-47 hint for Whisper ("en", "es", …). Empty = auto-detect.
    # num_speakers: hint for pyannote diarization. 0 = auto-detect; 1–8 = fixed count.
    #   Fixed count (e.g. 2) improves boundary accuracy for known speaker setups.
    window_ms: int = 1000
    transcribe_lang: str = ""
    num_speakers: int = 0


class SessionResponse(BaseModel):
    session_id: str
    state: str
    elcor: bool
    tier: str  # "free" | "paid" | "premium"


@router.post("/start", response_model=SessionResponse)
async def start_session(
    request: Request,
    req: StartRequest = StartRequest(),
) -> SessionResponse:
    """Start a new annotation session and begin streaming VoiceFrames."""
    # In cloud mode, user_id was set by CloudAuthMiddleware.
    # In self-hosted mode, fall back to the per-request key or env var.
    user_id: str | None = getattr(request.state, "cf_user", None) if settings.cloud_mode else None
    license_key: str | None = None if settings.cloud_mode else req.license_key

    tier = tiers.get_tier(license_key=license_key, user_id=user_id)

    session = await session_store.create_session(
        elcor=req.elcor,
        tier=tier,
        user_id=user_id or "",
        target_lang=req.target_lang,
        byok_deepl_key=req.byok_deepl_key,
        window_ms=max(100, (req.window_ms // 100) * 100),  # round down to nearest 100ms
        transcribe_lang=req.transcribe_lang,
        num_speakers=max(0, min(8, req.num_speakers)),  # clamp 0–8
    )
    return SessionResponse(
        session_id=session.session_id,
        state=session.state,
        elcor=session.elcor,
        tier=tier,
    )


@router.delete("/{session_id}/end")
async def end_session(session_id: str) -> dict:
    """Stop a session and release its classifier."""
    removed = await session_store.end_session(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"session_id": session_id, "state": "stopped"}


@router.get("/{session_id}")
def get_session(request: Request, session_id: str) -> SessionResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    user_id: str | None = getattr(request.state, "cf_user", None) if settings.cloud_mode else None
    license_key: str | None = None if settings.cloud_mode else request.headers.get("X-CF-License-Key")
    tier = tiers.get_tier(license_key=license_key, user_id=user_id)
    return SessionResponse(
        session_id=session.session_id,
        state=session.state,
        elcor=session.elcor,
        tier=tier,
    )
