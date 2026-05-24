"""Dashboard router.

Aggregated views for the React dashboard. Endpoints delegate to
app.services.dashboard_service and return app.schemas.dashboard view
models.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.core.config import load_settings
from app.core.security import get_current_workspace
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardHealthStatus,
    DashboardMetric,
    DashboardOverview,
    DashboardRepoCard,
)
from app.services import dashboard_service

logger = logging.getLogger("slothops.api.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(workspace_id: str = Depends(get_current_workspace)):
    settings = load_settings()
    return await dashboard_service.build_overview(workspace_id, settings.database_path)


@router.get("/activity", response_model=list[DashboardActivityItem])
async def get_activity(
    limit: int = 50,
    workspace_id: str = Depends(get_current_workspace),
):
    settings = load_settings()
    return await dashboard_service.build_activity(
        workspace_id, settings.database_path, limit=min(limit, 200),
    )


@router.get("/metrics", response_model=list[DashboardMetric])
async def get_metrics(workspace_id: str = Depends(get_current_workspace)):
    settings = load_settings()
    return await dashboard_service.build_metrics(workspace_id, settings.database_path)


@router.get("/repos", response_model=list[DashboardRepoCard])
async def get_repos(workspace_id: str = Depends(get_current_workspace)):
    settings = load_settings()
    return await dashboard_service.build_repo_cards(workspace_id, settings.database_path)


@router.get("/health", response_model=DashboardHealthStatus)
async def get_health(workspace_id: str = Depends(get_current_workspace)):
    settings = load_settings()
    return await dashboard_service.build_health(workspace_id, settings.database_path)
