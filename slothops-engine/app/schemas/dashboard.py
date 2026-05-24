"""Dashboard view models.

Stub definitions for the dashboard-facing payloads called out in
the plan. Fields are intentionally minimal — extend as endpoints
get wired up.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    name: str
    value: float
    unit: str | None = None


class DashboardActivityItem(BaseModel):
    ts: datetime
    actor: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    metadata: dict[str, Any] = {}


class DashboardRepoCard(BaseModel):
    repo_name: str
    active: bool
    sentry_project_slug: str | None = None
    last_qa_status: str | None = None
    last_rollback_status: str | None = None
    open_issues: int = 0


class DashboardHealthStatus(BaseModel):
    github: str = "unknown"
    sentry: str = "unknown"
    llm: str = "unknown"
    database: str = "unknown"


class DashboardOverview(BaseModel):
    workspace_id: str
    metrics: list[DashboardMetric] = []
    repos: list[DashboardRepoCard] = []
    recent_activity: list[DashboardActivityItem] = []
    health: DashboardHealthStatus = DashboardHealthStatus()
