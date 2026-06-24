# app/tiers.py — tier gate checks
#
# Two validation paths:
#   Self-hosted: LINNET_LICENSE_KEY env var (or key passed per-request)
#                → cf-core validate_license() → Heimdall /v1/licenses/verify
#   Cloud mode:  user_id from X-CF-Session header
#                → Heimdall /admin/cloud/resolve (admin token required)
#
# Both paths cache results in-process for 30 minutes so a brief Heimdall
# outage does not interrupt active sessions.
#
# BYOK: user-supplied DeepL key bypasses the Paid gate for translation only.
#       Pass byok_deepl=True to require_paid() to enable this exception.
from __future__ import annotations

import logging
import time

import requests

from app.config import settings

logger = logging.getLogger(__name__)

_PRODUCT = "LNNT"
_CACHE_TTL = 1800  # 30 minutes — matches Heimdall offline grace window

# Cache: cache_key (str) -> (tier: str, expires_at: float)
_cache: dict[str, tuple[str, float]] = {}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _cached(cache_key: str) -> str | None:
    entry = _cache.get(cache_key)
    if entry and time.monotonic() < entry[1]:
        return entry[0]
    return None


def _store(cache_key: str, tier: str) -> str:
    _cache[cache_key] = (tier, time.monotonic() + _CACHE_TTL)
    return tier


def _resolve_by_key(license_key: str) -> str:
    """Hit Heimdall /v1/licenses/verify for a raw key. Returns tier string."""
    cache_key = f"key:{license_key}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.post(
            f"{settings.heimdall_url}/v1/licenses/verify",
            json={"key": license_key, "min_tier": "free"},
            timeout=5,
        )
        if not resp.ok:
            logger.warning("[tiers] Heimdall /verify returned %s", resp.status_code)
            return _store(cache_key, "free")
        data = resp.json()
        if not data.get("valid", False):
            return _store(cache_key, "free")
        tier = data.get("tier", "free") or "free"
        return _store(cache_key, tier)
    except Exception as exc:
        logger.warning("[tiers] Heimdall key validation failed: %s", exc)
        # Do NOT cache on network failure — allow retry after next request
        return "free"


def _resolve_by_user(user_id: str) -> str:
    """Hit Heimdall /admin/cloud/resolve for a cloud user. Returns tier string."""
    if not settings.heimdall_admin_token:
        logger.warning("[tiers] HEIMDALL_ADMIN_TOKEN not set — defaulting to free")
        return "free"

    cache_key = f"user:{user_id}"
    cached = _cached(cache_key)
    if cached is not None:
        return cached

    try:
        resp = requests.post(
            f"{settings.heimdall_url}/admin/cloud/resolve",
            json={"user_id": user_id, "product": _PRODUCT},
            headers={"Authorization": f"Bearer {settings.heimdall_admin_token}"},
            timeout=5,
        )
        if not resp.ok:
            logger.warning("[tiers] Heimdall /cloud/resolve returned %s", resp.status_code)
            return _store(cache_key, "free")
        data = resp.json()
        tier = data.get("tier", "free") or "free"
        return _store(cache_key, tier)
    except Exception as exc:
        logger.warning("[tiers] Heimdall cloud resolve failed: %s", exc)
        return "free"


# ── Public API ────────────────────────────────────────────────────────────────

def get_tier(
    license_key: str | None = None,
    user_id: str | None = None,
) -> str:
    """
    Return the active tier for this request context.

    Precedence:
      1. user_id (cloud mode — set by CloudAuthMiddleware on request.state.cf_user)
      2. license_key argument (self-hosted, passed per-request)
      3. LINNET_LICENSE_KEY env var (self-hosted, instance-wide)
      4. "free" (no key configured)
    """
    if user_id:
        return _resolve_by_user(user_id)

    key = license_key or settings.linnet_license_key
    if not key:
        return "free"

    return _resolve_by_key(key)


def is_paid(
    license_key: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Return True if the resolved tier is paid or premium."""
    return get_tier(license_key=license_key, user_id=user_id) in ("paid", "premium")


def require_paid(
    license_key: str | None = None,
    user_id: str | None = None,
    byok_deepl: bool = False,
) -> None:
    """
    Raise HTTP 402 if caller doesn't have a Paid+ license.

    byok_deepl=True skips the check — the caller has provided their own
    DeepL API key and bypasses the Paid gate for translation only.
    """
    if byok_deepl:
        return
    if not is_paid(license_key=license_key, user_id=user_id):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=402,
            detail="This feature requires a Linnet Paid license. "
                   "Get one at circuitforge.tech.",
        )


# ── Backwards-compat shim (old call sites that pass key as positional) ────────

BYOK_UNLOCKABLE = ["cloud_stt", "cloud_tts", "session_pinning"]
