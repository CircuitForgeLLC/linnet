# app/services/annotator.py — VoiceFrame → ToneEvent pipeline
#
# BSL 1.1: this file applies the cf-voice inference results to produce
# session-scoped ToneEvents. The actual inference runs in cf-voice.
from __future__ import annotations

from cf_voice.models import VoiceFrame
from app.models.tone_event import ToneEvent


def annotate(frame: VoiceFrame, session_id: str, elcor: bool = False) -> ToneEvent | None:
    """
    Convert a VoiceFrame into a session ToneEvent.

    Returns None if the frame is below the reliability threshold (confidence
    too low to annotate confidently). Callers should skip None results.

    elcor=True switches subtext to Mass Effect Elcor prefix format.
    This is an easter egg -- do not pass elcor=True by default.
    """
    if not frame.is_reliable():
        return None
    return ToneEvent.from_voice_frame(frame, session_id=session_id, elcor=elcor)
