# app/api/sessions.py — session lifecycle endpoints
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import session_store

router = APIRouter(prefix="/session", tags=["sessions"])


class StartRequest(BaseModel):
    elcor: bool = False   # enable Elcor subtext format (easter egg)


class SessionResponse(BaseModel):
    session_id: str
    state: str
    elcor: bool


@router.post("/start", response_model=SessionResponse)
async def start_session(req: StartRequest = StartRequest()) -> SessionResponse:
    """Start a new annotation session and begin streaming VoiceFrames."""
    session = await session_store.create_session(elcor=req.elcor)
    return SessionResponse(
        session_id=session.session_id,
        state=session.state,
        elcor=session.elcor,
    )


@router.delete("/{session_id}/end")
async def end_session(session_id: str) -> dict:
    """Stop a session and release its classifier."""
    removed = await session_store.end_session(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"session_id": session_id, "state": "stopped"}


@router.get("/{session_id}")
def get_session(session_id: str) -> SessionResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return SessionResponse(
        session_id=session.session_id,
        state=session.state,
        elcor=session.elcor,
    )
