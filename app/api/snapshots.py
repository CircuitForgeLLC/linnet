# app/api/snapshots.py — session snapshot list and resume (Paid tier)
#
# Snapshots are saved automatically when a Paid session ends with history.
# Users can list their past sessions and resume them (imports history into a new session).
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app import tiers
from app.config import settings
from app.db import get_db
from app.services import session_store

router = APIRouter(tags=["snapshots"])


def _resolve_user_id(request: Request) -> str:
    """Return the cloud user_id from request state, or empty string for self-hosted."""
    return getattr(request.state, "cf_user", "") if settings.cloud_mode else ""


# ── List snapshots ────────────────────────────────────────────────────────────

class SnapshotSummary(BaseModel):
    id: str
    session_id: str
    created_at: float
    ended_at: float
    elcor: bool
    event_count: int


@router.get("/sessions/history", response_model=list[SnapshotSummary])
def list_snapshots(
    request: Request,
    limit: int = 20,
    conn=Depends(get_db),
) -> list[SnapshotSummary]:
    """
    Return the user's last N saved sessions (Paid tier only).

    Self-hosted: scoped to the instance (user_id = '').
    Cloud: scoped to the authenticated user.
    """
    user_id = _resolve_user_id(request)
    license_key = None if settings.cloud_mode else request.headers.get("X-CF-License-Key")
    tiers.require_paid(license_key=license_key, user_id=user_id or None)

    rows = conn.execute(
        """
        SELECT id, session_id, created_at, ended_at, elcor, event_count
        FROM session_snapshots
        WHERE user_id = ?
        ORDER BY ended_at DESC
        LIMIT ?
        """,
        (user_id, min(limit, 100)),
    ).fetchall()

    return [
        SnapshotSummary(
            id=row[0],
            session_id=row[1],
            created_at=row[2],
            ended_at=row[3],
            elcor=bool(row[4]),
            event_count=row[5],
        )
        for row in rows
    ]


# ── Resume a snapshot ─────────────────────────────────────────────────────────

class ResumeRequest(BaseModel):
    snapshot_id: str
    elcor: bool | None = None       # override Elcor mode; None = use snapshot's setting
    target_lang: str = ""
    byok_deepl_key: str = ""
    license_key: str | None = None  # self-hosted key


class ResumeResponse(BaseModel):
    session_id: str
    state: str
    elcor: bool
    tier: str
    resumed_from: str               # snapshot_id
    event_count: int                # number of historical events injected


@router.post("/session/resume", response_model=ResumeResponse)
async def resume_session(
    request: Request,
    req: ResumeRequest,
    conn=Depends(get_db),
) -> ResumeResponse:
    """
    Resume a previous session by restoring its annotation history into a new session.

    The new session starts fresh (new session_id, new classifier) but is pre-populated
    with the historical ToneEvents from the snapshot so the frontend can display them.

    Paid tier only. The snapshot must belong to the authenticated user.
    """
    user_id = _resolve_user_id(request)
    license_key = None if settings.cloud_mode else req.license_key
    tiers.require_paid(license_key=license_key, user_id=user_id or None)

    tier = tiers.get_tier(license_key=license_key, user_id=user_id or None)

    row = conn.execute(
        "SELECT session_id, elcor, events_json FROM session_snapshots WHERE id = ? AND user_id = ?",
        (req.snapshot_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    orig_session_id, orig_elcor, events_json = row
    use_elcor = req.elcor if req.elcor is not None else bool(orig_elcor)

    session = await session_store.create_session(
        elcor=use_elcor,
        tier=tier,
        user_id=user_id,
        target_lang=req.target_lang,
        byok_deepl_key=req.byok_deepl_key,
    )

    # Inject historical events so the frontend can render the prior session
    from app.models.tone_event import ToneEvent
    events_data = json.loads(events_json)
    for ev in events_data:
        tone = ToneEvent(
            session_id=session.session_id,
            label=ev["label"],
            confidence=ev["confidence"],
            speaker_id=ev.get("speaker_id", "speaker_a"),
            shift_magnitude=ev.get("shift_magnitude", 0.0),
            timestamp=ev["timestamp"],
            subtext=ev.get("subtext", ""),
            affect=ev.get("affect", ""),
        )
        session.history.append(tone)

    return ResumeResponse(
        session_id=session.session_id,
        state=session.state,
        elcor=session.elcor,
        tier=tier,
        resumed_from=req.snapshot_id,
        event_count=len(events_data),
    )
