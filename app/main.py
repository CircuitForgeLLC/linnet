# app/main.py — Linnet FastAPI application factory
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audio, events, export, history, sessions
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="Linnet",
    description="Real-time tone annotation — Elcor-style subtext for ND/autistic users",
    version="0.1.0",
)

# ── Mode middleware (applied before CORS so headers are always present) ──────
if settings.demo_mode:
    from app.middleware.demo import DemoModeMiddleware
    app.add_middleware(DemoModeMiddleware)
    logging.getLogger(__name__).info("DEMO_MODE active")

if settings.cloud_mode:
    from app.middleware.cloud import CloudAuthMiddleware
    app.add_middleware(CloudAuthMiddleware)
    logging.getLogger(__name__).info("CLOUD_MODE active")

# ── CORS ─────────────────────────────────────────────────────────────────────
_frontend_port = str(settings.linnet_frontend_port)
_origins = [
    f"http://localhost:{_frontend_port}",
    f"http://127.0.0.1:{_frontend_port}",
]
if settings.cloud_mode:
    _origins += [
        "https://menagerie.circuitforge.tech",
        "https://circuitforge.tech",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(sessions.router)
app.include_router(events.router)
app.include_router(history.router)
app.include_router(audio.router)
app.include_router(export.router)


@app.get("/health")
def health() -> dict:
    mode = "demo" if settings.demo_mode else ("cloud" if settings.cloud_mode else "dev")
    return {"status": "ok", "service": "linnet", "mode": mode}
