# tests/test_tiers.py
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.tiers import is_paid, require_paid


def test_valid_linnet_key():
    assert is_paid("CFG-LNNT-AAAA-BBBB-CCCC") is True


def test_invalid_prefix():
    assert is_paid("CFG-PRNG-AAAA-BBBB-CCCC") is False


def test_empty_key():
    assert is_paid("") is False


def test_none_key():
    assert is_paid(None) is False  # type: ignore[arg-type]


def test_require_paid_raises_402():
    with pytest.raises(HTTPException) as exc_info:
        require_paid(license_key="bad-key")
    assert exc_info.value.status_code == 402


def test_require_paid_passes():
    # Should not raise
    require_paid(license_key="CFG-LNNT-AAAA-BBBB-CCCC")
