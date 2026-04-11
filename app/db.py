# app/db.py — SQLite connection and migration runner for Linnet
#
# Used only for corrections storage (tone annotation training data).
# Session state is in-memory; this DB persists user-submitted corrections.
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from circuitforge_core.db import run_migrations

from app.config import settings

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _db_path() -> Path:
    path = Path(settings.linnet_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    run_migrations(conn, _MIGRATIONS_DIR)
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency — yields a connection, closes on teardown."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
