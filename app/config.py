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

    # Free tier: kill session this many seconds after the last SSE subscriber leaves.
    # Covers mobile tab timeout / screen lock / crash.
    session_idle_ttl_s: int = int(os.getenv("SESSION_IDLE_TTL_S", "90"))
    # Paid tier: hard idle timeout — kill session this many seconds after the last
    # annotation event, regardless of subscriber state. 30 minutes default.
    session_paid_ttl_s: int = int(os.getenv("SESSION_PAID_TTL_S", "1800"))

    # DeepL API key for CF-managed cloud translation (Paid tier).
    # BYOK users supply their own key per-session in StartRequest.byok_deepl_key.
    deepl_api_key: str = os.getenv("DEEPL_API_KEY", "")

    # CLOUD: where Caddy injects the cf_session user token
    cloud_session_header: str = os.getenv("CLOUD_SESSION_HEADER", "X-CF-Session")
    cloud_data_root: str = os.getenv("CLOUD_DATA_ROOT", "/devl/linnet-cloud-data")

    heimdall_url: str = os.getenv("HEIMDALL_URL", "https://license.circuitforge.tech")
    # Admin token for cloud-mode user tier resolution (/admin/cloud/resolve).
    # Not required for self-hosted installs; required when CLOUD_MODE=true.
    heimdall_admin_token: str = os.getenv("HEIMDALL_ADMIN_TOKEN", "")
    # Self-hosted license key. Cloud mode resolves tier via user_id instead.
    linnet_license_key: str = os.getenv("LINNET_LICENSE_KEY", "")

    linnet_port: int = int(os.getenv("LINNET_PORT", "8522"))
    linnet_frontend_port: int = int(os.getenv("LINNET_FRONTEND_PORT", "8521"))
    linnet_base_url: str = os.getenv("LINNET_BASE_URL", "")

    # cf-orch coordinator URL — used to request a managed cf-voice instance per session.
    # When set, each session allocates a cf-voice sidecar via the coordinator REST API.
    cf_orch_url: str = os.getenv("CF_ORCH_URL", "")

    # cf-orch agent URL — local service lifecycle (start/stop). Separate from the
    # coordinator: coordinator is read/scheduling (:7700), agent is write (:7701).
    cf_orch_agent_url: str = os.getenv("CF_ORCH_AGENT_URL", "")

    # Static cf-voice sidecar URL — legacy override (bypasses cf-orch, points directly
    # at a running cf-voice process). Takes precedence over cf-orch allocation when set.
    cf_voice_url: str = os.getenv("CF_VOICE_URL", "")

    # Local SQLite DB for corrections storage. Shared across users on a single instance;
    # corrections contain text only (no audio). Cloud mode uses cloud_data_root prefix.
    linnet_db: str = os.getenv("LINNET_DB", "data/linnet.db")


settings = Settings()
