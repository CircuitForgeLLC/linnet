# tests/test_tiers.py — tier gate and Heimdall validation logic
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app import tiers


@pytest.fixture(autouse=True)
def clear_tier_cache():
    """Wipe the in-process tier cache between tests."""
    tiers._cache.clear()
    yield
    tiers._cache.clear()


# ── Key-based resolution ──────────────────────────────────────────────────────

def _mock_verify(tier: str, valid: bool = True):
    """Return a mock requests.Response for /v1/licenses/verify."""
    resp = MagicMock()
    resp.ok = valid
    resp.json.return_value = {"valid": valid, "tier": tier, "user_id": "u123"}
    return resp


def test_get_tier_free_when_no_key(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    assert tiers.get_tier() == "free"


def test_get_tier_paid_via_key(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    with patch("app.tiers.requests.post", return_value=_mock_verify("paid")) as mock_post:
        result = tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
    assert result == "paid"
    mock_post.assert_called_once()
    assert "/v1/licenses/verify" in mock_post.call_args[0][0]


def test_get_tier_free_on_invalid_key(monkeypatch):
    with patch("app.tiers.requests.post", return_value=_mock_verify("free", valid=False)):
        result = tiers.get_tier(license_key="CFG-LNNT-DEAD-BEEF-0000")
    assert result == "free"


def test_get_tier_free_on_heimdall_error(monkeypatch):
    with patch("app.tiers.requests.post", side_effect=Exception("timeout")):
        result = tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
    assert result == "free"


def test_get_tier_uses_env_key(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "CFG-LNNT-ENV0-ENV0-ENV0")
    with patch("app.tiers.requests.post", return_value=_mock_verify("paid")) as mock_post:
        result = tiers.get_tier()
    assert result == "paid"
    assert mock_post.call_args[1]["json"]["key"] == "CFG-LNNT-ENV0-ENV0-ENV0"


def test_key_result_is_cached(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    with patch("app.tiers.requests.post", return_value=_mock_verify("paid")) as mock_post:
        tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
        tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
    # Second call must hit cache, not Heimdall
    assert mock_post.call_count == 1


def test_network_error_does_not_cache(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    with patch("app.tiers.requests.post", side_effect=Exception("timeout")) as mock_post:
        tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
        tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
    # Network errors are NOT cached — both calls hit Heimdall
    assert mock_post.call_count == 2


# ── Cloud user resolution ─────────────────────────────────────────────────────

def _mock_cloud_resolve(tier: str):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"tier": tier, "user_id": "u456"}
    return resp


def test_get_tier_cloud_paid(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.heimdall_admin_token", "tok-admin")
    with patch("app.tiers.requests.post", return_value=_mock_cloud_resolve("paid")) as mock_post:
        result = tiers.get_tier(user_id="user-uuid-123")
    assert result == "paid"
    assert "/admin/cloud/resolve" in mock_post.call_args[0][0]


def test_get_tier_cloud_free_when_no_admin_token(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.heimdall_admin_token", "")
    result = tiers.get_tier(user_id="user-uuid-123")
    assert result == "free"


def test_user_id_takes_precedence_over_key(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.heimdall_admin_token", "tok-admin")
    with patch("app.tiers.requests.post", return_value=_mock_cloud_resolve("premium")) as mock_post:
        result = tiers.get_tier(license_key="CFG-LNNT-AAAA-BBBB-CCCC", user_id="u999")
    assert result == "premium"
    assert "/admin/cloud/resolve" in mock_post.call_args[0][0]


def test_cloud_result_is_cached(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.heimdall_admin_token", "tok-admin")
    with patch("app.tiers.requests.post", return_value=_mock_cloud_resolve("paid")) as mock_post:
        tiers.get_tier(user_id="u-cached")
        tiers.get_tier(user_id="u-cached")
    assert mock_post.call_count == 1


# ── is_paid() and require_paid() ─────────────────────────────────────────────

def test_is_paid_true_for_paid_tier(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    with patch("app.tiers.requests.post", return_value=_mock_verify("paid")):
        assert tiers.is_paid(license_key="CFG-LNNT-AAAA-BBBB-CCCC") is True


def test_is_paid_true_for_premium_tier(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    with patch("app.tiers.requests.post", return_value=_mock_verify("premium")):
        assert tiers.is_paid(license_key="CFG-LNNT-PREM-PREM-PREM") is True


def test_is_paid_false_for_free(monkeypatch):
    monkeypatch.setattr("app.tiers.settings.linnet_license_key", "")
    assert tiers.is_paid() is False


def test_require_paid_raises_402_for_free():
    with patch("app.tiers.get_tier", return_value="free"):
        with pytest.raises(HTTPException) as exc_info:
            tiers.require_paid()
    assert exc_info.value.status_code == 402


def test_require_paid_passes_for_paid():
    with patch("app.tiers.get_tier", return_value="paid"):
        tiers.require_paid()  # must not raise


def test_require_paid_byok_skips_check():
    # byok_deepl=True bypasses the tier gate regardless of tier
    with patch("app.tiers.get_tier", return_value="free") as mock_get:
        tiers.require_paid(byok_deepl=True)  # must not raise
    mock_get.assert_not_called()
