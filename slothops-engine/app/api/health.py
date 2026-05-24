"""Health & liveness endpoints.

Migrated out of main.py as the first validation slice of the
restructure. Routes are unchanged so existing callers keep working.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.config import load_settings
from app.core.security import get_current_workspace

logger = logging.getLogger("slothops.api.health")

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "slothops-engine"}


@router.get("/api/health/engine")
async def health_engine() -> dict[str, str]:
    settings = load_settings()
    return {
        "status": "ok",
        "engine": "SlothOps",
        "version": "0.2.0",
        "database": settings.database_path,
    }


@router.get("/api/health/llm")
async def health_llm(workspace_id: str = Depends(get_current_workspace)) -> dict:
    try:
        from genai_client import health_check
        return await health_check()
    except Exception as e:
        logger.error("LLM health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}
