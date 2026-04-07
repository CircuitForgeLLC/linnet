# app/middleware/demo.py — DEMO_MODE restrictions
#
# When DEMO_MODE=true:
#   - Session creation is capped at DEMO_MAX_SESSIONS concurrent sessions
#   - Export endpoint returns 403 (no personal data leaves the demo server)
#   - Response header X-Linnet-Mode: demo on all responses
#   - CF_VOICE_MOCK is forced on (see compose.demo.yml)
from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.services import session_store


class DemoModeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Block export in demo mode — no data leaves the demo server
        if path.endswith("/export"):
            return JSONResponse(
                status_code=403,
                content={"detail": "Export is disabled in demo mode."},
            )

        # Cap concurrent session creation
        if path == "/session/start" and request.method == "POST":
            active = session_store.active_session_count()
            if active >= settings.demo_max_sessions:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            f"Demo server is at capacity ({settings.demo_max_sessions} "
                            "active sessions). Please try again in a moment."
                        )
                    },
                )

        response = await call_next(request)
        response.headers["X-Linnet-Mode"] = "demo"
        return response
