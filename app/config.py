# app/config.py — runtime mode settings
from __future__ import annotations

import os


class Settings:
    """Read-once settings from environment variables."""

    demo_mode: bool = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
    cloud_mode: bool = os.getenv("CLOUD_MODE", "").lower() in ("1", "true", "yes")

    # DEMO: max simultaneous active sessions (prevents resource abuse on the demo server)
    demo_max_sessions: int = int(os.getenv("DEMO_MAX_SESSIONS", "3"))
    # DEMO: auto-kill sessions after this many seconds of inactivity
    demo_session_ttl_s: int = int(os.getenv("DEMO_SESSION_TTL_S", "300"))  # 5 min

    # All modes: kill a session this many seconds after its last SSE subscriber
    # disconnects. Covers mobile tab timeout / screen lock / crash.
    # Set generously enough to survive a brief screen-off without losing the session,
    # but short enough that zombie sessions don't accumulate.
    session_idle_ttl_s: int = int(os.getenv("SESSION_IDLE_TTL_S", "90"))

    # CLOUD: where Caddy injects the cf_session user token
    cloud_session_header: str = os.getenv("CLOUD_SESSION_HEADER", "X-CF-Session")
    cloud_data_root: str = os.getenv("CLOUD_DATA_ROOT", "/devl/linnet-cloud-data")

    heimdall_url: str = os.getenv("HEIMDALL_URL", "https://license.circuitforge.tech")

    linnet_port: int = int(os.getenv("LINNET_PORT", "8522"))
    linnet_frontend_port: int = int(os.getenv("LINNET_FRONTEND_PORT", "8521"))
    linnet_base_url: str = os.getenv("LINNET_BASE_URL", "")

    # cf-orch coordinator URL — used to request a managed cf-voice instance per session.
    # When set, each session allocates a cf-voice sidecar via the coordinator REST API.
    cf_orch_url: str = os.getenv("CF_ORCH_URL", "")

    # Static cf-voice sidecar URL — legacy override (bypasses cf-orch, points directly
    # at a running cf-voice process). Takes precedence over cf-orch allocation when set.
    cf_voice_url: str = os.getenv("CF_VOICE_URL", "")

    # Local SQLite DB for corrections storage. Shared across users on a single instance;
    # corrections contain text only (no audio). Cloud mode uses cloud_data_root prefix.
    linnet_db: str = os.getenv("LINNET_DB", "data/linnet.db")


settings = Settings()
