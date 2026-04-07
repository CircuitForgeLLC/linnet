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

    # CLOUD: where Caddy injects the cf_session user token
    cloud_session_header: str = os.getenv("CLOUD_SESSION_HEADER", "X-CF-Session")
    cloud_data_root: str = os.getenv("CLOUD_DATA_ROOT", "/devl/linnet-cloud-data")

    heimdall_url: str = os.getenv("HEIMDALL_URL", "https://license.circuitforge.tech")

    linnet_port: int = int(os.getenv("LINNET_PORT", "8522"))
    linnet_frontend_port: int = int(os.getenv("LINNET_FRONTEND_PORT", "8521"))
    linnet_base_url: str = os.getenv("LINNET_BASE_URL", "")


settings = Settings()
