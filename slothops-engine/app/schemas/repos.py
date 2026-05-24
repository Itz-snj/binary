"""Repo view models exposed to the dashboard."""

from typing import Any

from pydantic import BaseModel


class RepoSummary(BaseModel):
    repo_name: str
    active: bool
    default_branch: str | None = None
    sentry_project_slug: str | None = None
    policy: dict[str, Any] = {}
    last_qa_status: str | None = None
    last_rollback_status: str | None = None


class WorkspaceSummary(BaseModel):
    workspace_id: str
    name: str
    repo_count: int
    github_connected: bool
    sentry_connected: bool
