# app/tiers.py — tier gate checks
#
# Free tier: local inference only, no license key required.
# Paid tier: cloud STT/TTS fallback, session pinning (v1.0).
from __future__ import annotations

import os

BYOK_UNLOCKABLE = ["cloud_stt", "cloud_tts", "session_pinning"]


def is_paid(license_key: str | None = None) -> bool:
    """Return True if the request has a valid Paid+ license key."""
    key = license_key or os.environ.get("LINNET_LICENSE_KEY", "")
    # Paid keys start with CFG-LNNT- (format: CFG-LNNT-XXXX-XXXX-XXXX)
    return bool(key) and key.upper().startswith("CFG-LNNT-")


def require_free() -> None:
    """No-op. All users get Free tier features."""


def require_paid(license_key: str | None = None) -> None:
    """Raise if caller doesn't have a Paid license."""
    if not is_paid(license_key):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=402,
            detail="This feature requires a Linnet Paid license. "
                   "Get one at circuitforge.tech.",
        )
