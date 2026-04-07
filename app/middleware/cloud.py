# app/middleware/cloud.py — CLOUD_MODE auth
#
# When CLOUD_MODE=true, all /session/* routes require the X-CF-Session header
# (injected by Caddy from the cf_session cookie set by the website auth flow).
# The header value is forwarded opaquely — Linnet trusts it as an opaque user ID.
# Full Heimdall JWT validation is a v1.0 addition (tracked in linnet#16).
from __future__ import annotations

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# Paths that don't require auth even in cloud mode
_PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class CloudAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in _PUBLIC_PATHS or not path.startswith("/session"):
            return await call_next(request)

        session_token = request.headers.get(settings.cloud_session_header, "").strip()
        if not session_token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Sign in at circuitforge.tech."},
            )

        # Attach the user identity to request state so endpoints can use it
        request.state.cf_user = session_token
        response = await call_next(request)
        response.headers["X-Linnet-Mode"] = "cloud"
        return response
