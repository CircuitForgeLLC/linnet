# app/api/dev.py — dev-only endpoints for local service management
#
# Proxies stop/start calls to the cf-orch agent so the frontend dev panel
# doesn't need to know the agent URL directly.
# Not registered in cloud or demo mode.
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/dev", tags=["dev"])
logger = logging.getLogger(__name__)


def _agent_url() -> str:
    url = settings.cf_orch_agent_url
    if not url:
        raise HTTPException(503, detail="CF_ORCH_AGENT_URL not configured")
    return url.rstrip("/")


@router.post("/voice/stop")
async def voice_stop() -> dict:
    """Stop the cf-voice sidecar via the cf-orch agent."""
    agent = _agent_url()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(f"{agent}/services/cf-voice/stop", json={})
        except httpx.RequestError as exc:
            raise HTTPException(502, detail=f"Agent unreachable: {exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, detail=resp.text)
    logger.info("dev: cf-voice stop → %s", resp.status_code)
    return {"ok": True, "action": "stop"}


@router.post("/voice/start")
async def voice_start() -> dict:
    """Start the cf-voice sidecar via the cf-orch agent."""
    agent = _agent_url()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(f"{agent}/services/cf-voice/start", json={})
        except httpx.RequestError as exc:
            raise HTTPException(502, detail=f"Agent unreachable: {exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, detail=resp.text)
    logger.info("dev: cf-voice start → %s", resp.status_code)
    return {"ok": True, "action": "start"}


@router.post("/voice/restart")
async def voice_restart() -> dict:
    """Stop then start cf-voice via the cf-orch agent."""
    import asyncio

    agent = _agent_url()
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(f"{agent}/services/cf-voice/stop", json={})
        except httpx.RequestError as exc:
            raise HTTPException(502, detail=f"Agent unreachable on stop: {exc}") from exc

    # Give the process time to fully exit before start fires
    await asyncio.sleep(2.0)

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(f"{agent}/services/cf-voice/start", json={})
        except httpx.RequestError as exc:
            raise HTTPException(502, detail=f"Agent unreachable on start: {exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, detail=resp.text)
    logger.info("dev: cf-voice restart complete")
    return {"ok": True, "action": "restart"}
