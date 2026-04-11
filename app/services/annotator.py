# app/services/annotator.py — VoiceFrame → ToneEvent pipeline
#
# BSL 1.1: this file applies the cf-voice inference results to produce
# session-scoped ToneEvents. The actual inference runs in cf-voice.
from __future__ import annotations

from cf_voice.models import VoiceFrame
from app.models.tone_event import ToneEvent


def annotate(
    frame: VoiceFrame,
    session_id: str,
    elcor: bool = False,
    threshold: float = 0.10,
) -> ToneEvent | None:
    """
    Convert a VoiceFrame into a session ToneEvent.

    Returns None if the frame is below the reliability threshold. The default
    0.25 is calibrated for real wav2vec2 SER inference, which routinely scores
    0.15-0.45 on conversational audio. The mock used 0.6 (mock confidence was
    artificially inflated).

    elcor=True switches subtext to bracketed tone-prefix format (easter egg).
    """
    if not frame.is_reliable(threshold=threshold):
        return None
    return ToneEvent.from_voice_frame(frame, session_id=session_id, elcor=elcor)
