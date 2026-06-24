# tests/test_pinning.py — session pinning (Paid tier TTL) and translator
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.models.session import Session
from app.services import session_store
from app.services.translator import Translator


@pytest.fixture(autouse=True)
def clean_sessions():
    session_store._sessions.clear()
    session_store._tasks.clear()
    session_store._audio_buffers.clear()
    yield
    session_store._sessions.clear()
    session_store._tasks.clear()
    session_store._audio_buffers.clear()


# ── Tier-aware reaper (_should_reap) ─────────────────────────────────────────

def test_free_session_reaped_after_subscriber_leaves(monkeypatch):
    monkeypatch.setattr("app.services.session_store.settings.session_idle_ttl_s", 0)
    s = Session(tier="free")
    s.state = "running"
    q = s.subscribe()
    s.unsubscribe(q)  # triggers last_subscriber_left_at
    now = time.monotonic() + 1
    assert session_store._should_reap(s, now) is True


def test_free_session_spared_while_subscriber_active(monkeypatch):
    monkeypatch.setattr("app.services.session_store.settings.session_idle_ttl_s", 0)
    s = Session(tier="free")
    s.state = "running"
    s.subscribe()
    now = time.monotonic() + 9999
    assert session_store._should_reap(s, now) is False


def test_paid_session_reaped_on_activity_timeout(monkeypatch):
    monkeypatch.setattr("app.services.session_store.settings.session_paid_ttl_s", 0)
    s = Session(tier="paid")
    s.state = "running"
    now = time.monotonic() + 1
    assert session_store._should_reap(s, now) is True


def test_paid_session_spared_within_activity_window(monkeypatch):
    monkeypatch.setattr("app.services.session_store.settings.session_paid_ttl_s", 9999)
    s = Session(tier="paid")
    s.state = "running"
    now = time.monotonic() + 1
    assert session_store._should_reap(s, now) is False


def test_paid_session_not_reaped_despite_no_subscribers(monkeypatch):
    """Paid tier ignores subscriber state — activity window is what matters."""
    monkeypatch.setattr("app.services.session_store.settings.session_paid_ttl_s", 9999)
    s = Session(tier="paid")
    s.state = "running"
    q = s.subscribe()
    s.unsubscribe(q)  # no subscribers now
    now = time.monotonic() + 200  # past free-tier TTL but within paid TTL
    assert session_store._should_reap(s, now) is False


def test_stopped_session_never_reaped():
    s = Session(tier="free")
    s.state = "stopped"
    assert session_store._should_reap(s, time.monotonic() + 9999) is False


def test_broadcast_updates_last_activity_at():
    from app.models.tone_event import ToneEvent
    s = Session(tier="paid")
    before = s.last_activity_at
    time.sleep(0.01)
    tone = ToneEvent(
        session_id=s.session_id, label="Neutral", confidence=0.9,
        speaker_id="speaker_a", shift_magnitude=0.0, timestamp=0.0,
        subtext="", affect="neutral",
    )
    s.broadcast(tone)
    assert s.last_activity_at > before


# ── Snapshot save on end ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_snapshot_saved_for_paid_session_with_history():
    from app.models.tone_event import ToneEvent
    session = await session_store.create_session(tier="paid", user_id="u1")
    tone = ToneEvent(
        session_id=session.session_id, label="Stressed", confidence=0.85,
        speaker_id="Speaker A", shift_magnitude=0.1, timestamp=1.0,
        subtext="", affect="stressed",
    )
    session.history.append(tone)

    with patch("app.services.session_store._save_snapshot") as mock_save:
        await session_store.end_session(session.session_id)
    mock_save.assert_called_once_with(session)


@pytest.mark.asyncio
async def test_snapshot_not_saved_for_free_session():
    session = await session_store.create_session(tier="free", user_id="u1")
    from app.models.tone_event import ToneEvent
    tone = ToneEvent(
        session_id=session.session_id, label="Neutral", confidence=0.9,
        speaker_id="speaker_a", shift_magnitude=0.0, timestamp=0.0,
        subtext="", affect="neutral",
    )
    session.history.append(tone)

    with patch("app.services.session_store._save_snapshot") as mock_save:
        await session_store.end_session(session.session_id)
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_snapshot_not_saved_for_empty_paid_session():
    session = await session_store.create_session(tier="paid", user_id="u1")
    # No events in history
    with patch("app.services.session_store._save_snapshot") as mock_save:
        await session_store.end_session(session.session_id)
    mock_save.assert_not_called()


# ── Translator ────────────────────────────────────────────────────────────────

def _make_session(target_lang="", byok="", tier="free"):
    s = Session(tier=tier, target_lang=target_lang, byok_deepl_key=byok)
    return s


def _mock_deepl_resp(translated: str):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"translations": [{"text": translated}]}
    return resp


def test_translator_none_when_no_target_lang():
    s = _make_session(target_lang="")
    assert Translator.for_session(s) is None


def test_translator_none_when_no_key(monkeypatch):
    monkeypatch.setattr("app.services.translator.settings.deepl_api_key", "")
    s = _make_session(target_lang="fr")
    assert Translator.for_session(s) is None


def test_translator_uses_byok_key(monkeypatch):
    monkeypatch.setattr("app.services.translator.settings.deepl_api_key", "")
    s = _make_session(target_lang="fr", byok="my-deepl-key")
    t = Translator.for_session(s)
    assert t is not None
    assert t._url.endswith("api-free.deepl.com/v2/translate")


def test_translator_uses_cf_key(monkeypatch):
    monkeypatch.setattr("app.services.translator.settings.deepl_api_key", "cf-pro-key")
    s = _make_session(target_lang="es")
    t = Translator.for_session(s)
    assert t is not None
    assert t._url.endswith("api.deepl.com/v2/translate")


def test_translator_byok_takes_precedence_over_cf_key(monkeypatch):
    monkeypatch.setattr("app.services.translator.settings.deepl_api_key", "cf-pro-key")
    s = _make_session(target_lang="de", byok="user-free-key")
    t = Translator.for_session(s)
    assert t._url.endswith("api-free.deepl.com/v2/translate")
    assert t._api_key == "user-free-key"


def test_translate_calls_deepl():
    t = Translator(target_lang="fr", api_key="k", pro=False)
    with patch("app.services.translator.requests.post", return_value=_mock_deepl_resp("Stressé")):
        result = t.translate("Stressed")
    assert result == "Stressé"


def test_translate_caches_result():
    t = Translator(target_lang="fr", api_key="k", pro=False)
    with patch("app.services.translator.requests.post", return_value=_mock_deepl_resp("Stressé")) as mock_post:
        t.translate("Stressed")
        t.translate("Stressed")
    assert mock_post.call_count == 1


def test_translate_returns_original_on_error():
    t = Translator(target_lang="fr", api_key="k", pro=False)
    with patch("app.services.translator.requests.post", side_effect=Exception("timeout")):
        result = t.translate("Stressed")
    assert result == "Stressed"


def test_translate_target_lang_uppercased():
    t = Translator(target_lang="fr", api_key="k", pro=False)
    assert t._target_lang == "FR"


def test_translate_empty_label_returns_empty():
    t = Translator(target_lang="fr", api_key="k", pro=False)
    assert t.translate("") == ""
