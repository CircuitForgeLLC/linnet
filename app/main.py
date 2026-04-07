# app/main.py — Linnet FastAPI application factory
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audio, events, export, history, sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="Linnet",
    description="Real-time tone annotation — Elcor-style subtext for ND/autistic users",
    version="0.1.0",
)

# CORS: allow localhost frontend dev server and same-origin in production
_frontend_port = os.getenv("LINNET_FRONTEND_PORT", "8521")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{_frontend_port}",
        "http://127.0.0.1:" + _frontend_port,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(events.router)
app.include_router(history.router)
app.include_router(audio.router)
app.include_router(export.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "linnet"}
