# tests/test_tone_event.py
from __future__ import annotations

import json

import pytest

from app.models.tone_event import ToneEvent


def _event(**kwargs) -> ToneEvent:
    defaults = dict(
        label="Neutral statement",
        confidence=0.8,
        speaker_id="speaker_a",
        shift_magnitude=0.0,
        timestamp=1000.0,
        session_id="sess-1",
        subtext="",
        affect="neutral",
        shift_direction="none",
        prosody_flags=[],
        elcor=False,
    )
    defaults.update(kwargs)
    return ToneEvent(**defaults)


def test_to_sse_format():
    evt = _event()
    sse = evt.to_sse()
    assert sse.startswith("event: tone-event\ndata: ")
    assert sse.endswith("\n\n")


def test_to_sse_json_fields():
    evt = _event(label="Frustration", affect="frustrated", confidence=0.9)
    sse = evt.to_sse()
    data_line = sse.split("data: ", 1)[1].rstrip()
    payload = json.loads(data_line)
    assert payload["label"] == "Frustration"
    assert payload["affect"] == "frustrated"
    assert payload["confidence"] == pytest.approx(0.9)
    assert "timestamp" in payload
    assert "session_id" in payload


def test_is_reliable_above_threshold():
    assert _event(confidence=0.7).is_reliable()


def test_is_reliable_below_threshold():
    assert not _event(confidence=0.5).is_reliable()


def test_is_reliable_custom_threshold():
    assert _event(confidence=0.4).is_reliable(threshold=0.3)
    assert not _event(confidence=0.4).is_reliable(threshold=0.5)


def test_elcor_subtext_in_sse():
    evt = _event(elcor=True, subtext="[Neutral — matter-of-fact delivery]")
    payload = json.loads(evt.to_sse().split("data: ", 1)[1].rstrip())
    assert payload["subtext"] == "[Neutral — matter-of-fact delivery]"
