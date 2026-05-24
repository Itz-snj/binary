"""
SlothOps Engine — SQLModel ORM Table Definitions
Proper Postgres types: JSONB for blobs, TIMESTAMPTZ for datetimes, Boolean for flags.
These are the database tables; Pydantic request/response models stay in models.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Users & Auth ─────────────────────────────────────────────────────────

class UserTable(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=_now, nullable=False)


class WorkspaceTable(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: str = Field(primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=_now, nullable=False)


class WorkspaceUserTable(SQLModel, table=True):
    __tablename__ = "workspace_users"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    role: str = Field(default="admin")


# ── Integrations ─────────────────────────────────────────────────────────

class IntegrationTable(SQLModel, table=True):
    __tablename__ = "integrations"

    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    github_installation_id: Optional[str] = None
    sentry_webhook_secret: Optional[str] = None


# ── Developer Config ──────────────────────────────────────────────────────

class DeveloperConfigTable(SQLModel, table=True):
    __tablename__ = "developer_configs"

    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    config_json: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    updated_at: datetime = Field(default_factory=_now, nullable=False)


# ── Issues ────────────────────────────────────────────────────────────────

class IssueTable(SQLModel, table=True):
    __tablename__ = "issues"

    id: str = Field(primary_key=True)
    workspace_id: str = Field(index=True, default="default_workspace")
    repo_name: Optional[str] = Field(default=None, index=True)
    fingerprint: str = Field(index=True)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None
    raw_payload: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    occurrence_count: int = Field(default=1)
    classification: str = Field(default="unknown")
    confidence: Optional[str] = None
    status: str = Field(default="received", index=True)
    fix_pr_url: Optional[str] = None
    fix_pr_branch: Optional[str] = None
    root_cause: Optional[str] = None
    recommendation: Optional[str] = None
    previous_fix_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now, nullable=False)
    updated_at: datetime = Field(default_factory=_now, nullable=False)


# ── QA Reports ───────────────────────────────────────────────────────────

class QAReportTable(SQLModel, table=True):
    __tablename__ = "qa_reports"

    id: str = Field(primary_key=True)
    workspace_id: str = Field(index=True)
    pr_number: int
    pr_url: str = Field(default="")
    commit_sha: str = Field(default="")
    repo_name: str = Field(default="", index=True)
    static_analysis: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    functionality: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    stress_test: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    vapt: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    regression: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    performance: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    triage: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    required_agents: list = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]")
    )
    advisory_agents: list = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]")
    )
    artifacts: list = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]")
    )
    overall_status: str = Field(default="running")
    summary: str = Field(default="")
    email_sent_to: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now, nullable=False)


# ── QA Configs ───────────────────────────────────────────────────────────

class QAConfigTable(SQLModel, table=True):
    __tablename__ = "qa_configs"

    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    config_json: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    updated_at: datetime = Field(default_factory=_now, nullable=False)


# ── Repo Configs ──────────────────────────────────────────────────────────

class RepoConfigTable(SQLModel, table=True):
    __tablename__ = "repo_configs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "repo_name", name="uq_repo_config"),
    )

    workspace_id: str = Field(foreign_key="workspaces.id", primary_key=True)
    repo_name: str = Field(primary_key=True)
    config_json: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    sentry_project_slug: Optional[str] = Field(default=None, index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_now, nullable=False)
    updated_at: datetime = Field(default_factory=_now, nullable=False)


# ── Webhook Deliveries ────────────────────────────────────────────────────

class WebhookDeliveryTable(SQLModel, table=True):
    __tablename__ = "webhook_deliveries"

    delivery_id: str = Field(primary_key=True)
    event_type: Optional[str] = None
    workspace_id: Optional[str] = None
    repo_name: Optional[str] = None
    received_at: datetime = Field(default_factory=_now, nullable=False)


# ── Audit Events ──────────────────────────────────────────────────────────

class AuditEventTable(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: str = Field(primary_key=True)
    workspace_id: str = Field(index=True)
    repo_name: Optional[str] = Field(default=None, index=True)
    actor: str = Field(default="slothops")
    action: str = Field(index=True)
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    metadata_json: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )
    created_at: datetime = Field(default_factory=_now, nullable=False, index=True)


# ── Rollbacks ─────────────────────────────────────────────────────────────

class RollbackTable(SQLModel, table=True):
    __tablename__ = "rollbacks"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "repo_name", "failed_commit_sha",
            name="uq_rollback_sha"
        ),
    )

    id: str = Field(primary_key=True)
    workspace_id: str = Field(index=True)
    repo_name: str = Field(index=True)
    failed_commit_sha: str
    rolled_back_to_sha: Optional[str] = None
    backup_branch: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    environment: Optional[str] = None
    deployment_ref: Optional[str] = None
    deployment_url: Optional[str] = None
    rollback_mode: str = Field(default="approval_required")
    rollback_strategy: str = Field(default="rollback_pr")
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_reason: Optional[str] = None
    failure_reason: str = Field(default="")
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=_now, nullable=False)
    updated_at: datetime = Field(default_factory=_now, nullable=False)


# ── Resolutions ───────────────────────────────────────────────────────────

class ResolutionTable(SQLModel, table=True):
    __tablename__ = "resolutions"

    id: str = Field(primary_key=True)
    rollback_id: str = Field(foreign_key="rollbacks.id", index=True)
    workspace_id: str = Field(index=True)
    repo_name: str
    backup_branch: str
    resolution_pr_url: Optional[str] = None
    resolution_pr_number: Optional[int] = None
    attempt_number: int = Field(default=1)
    build_error_log: str = Field(default="")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=_now, nullable=False)
    updated_at: datetime = Field(default_factory=_now, nullable=False)
