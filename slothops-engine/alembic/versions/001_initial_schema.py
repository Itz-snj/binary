"""001_initial_schema

Initial schema migration: all 13 SlothOps tables with proper Postgres types.
JSONB for config/agent blobs, TIMESTAMPTZ for datetimes, Boolean for flags.

Revision ID: 001
Revises:
Create Date: 2026-05-22
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── workspaces ───────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── workspace_users ──────────────────────────────────────────────────
    op.create_table(
        "workspace_users",
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(), nullable=False, server_default="admin"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    # ── integrations ─────────────────────────────────────────────────────
    op.create_table(
        "integrations",
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("github_installation_id", sa.String(), nullable=True),
        sa.Column("sentry_webhook_secret", sa.String(), nullable=True),
    )

    # ── developer_configs ─────────────────────────────────────────────────
    op.create_table(
        "developer_configs",
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── issues ────────────────────────────────────────────────────────────
    op.create_table(
        "issues",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False, server_default="default_workspace"),
        sa.Column("repo_name", sa.String(), nullable=True),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("function_name", sa.String(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("raw_payload", JSONB, nullable=True),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("classification", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="received"),
        sa.Column("fix_pr_url", sa.String(), nullable=True),
        sa.Column("fix_pr_branch", sa.String(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("previous_fix_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_issues_workspace_id", "issues", ["workspace_id"])
    op.create_index("ix_issues_repo_name", "issues", ["repo_name"])
    op.create_index("ix_issues_fingerprint", "issues", ["fingerprint"])
    op.create_index("ix_issues_status", "issues", ["status"])
    op.create_index("ix_issues_workspace_repo", "issues", ["workspace_id", "repo_name"])

    # ── qa_reports ────────────────────────────────────────────────────────
    op.create_table(
        "qa_reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pr_url", sa.String(), nullable=False, server_default=""),
        sa.Column("commit_sha", sa.String(), nullable=False, server_default=""),
        sa.Column("repo_name", sa.String(), nullable=False, server_default=""),
        sa.Column("static_analysis", JSONB, nullable=True),
        sa.Column("functionality", JSONB, nullable=True),
        sa.Column("stress_test", JSONB, nullable=True),
        sa.Column("vapt", JSONB, nullable=True),
        sa.Column("regression", JSONB, nullable=True),
        sa.Column("performance", JSONB, nullable=True),
        sa.Column("triage", JSONB, nullable=True),
        sa.Column("required_agents", JSONB, nullable=False, server_default="[]"),
        sa.Column("advisory_agents", JSONB, nullable=False, server_default="[]"),
        sa.Column("artifacts", JSONB, nullable=False, server_default="[]"),
        sa.Column("overall_status", sa.String(), nullable=False, server_default="running"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("email_sent_to", sa.String(), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_qa_reports_workspace_id", "qa_reports", ["workspace_id"])
    op.create_index("ix_qa_reports_repo_name", "qa_reports", ["repo_name"])

    # ── qa_configs ────────────────────────────────────────────────────────
    op.create_table(
        "qa_configs",
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("config_json", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── repo_configs ──────────────────────────────────────────────────────
    op.create_table(
        "repo_configs",
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("repo_name", sa.String(), primary_key=True),
        sa.Column("config_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("sentry_project_slug", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("workspace_id", "repo_name", name="uq_repo_config"),
    )
    op.create_index(
        "ix_repo_configs_sentry",
        "repo_configs",
        ["workspace_id", "sentry_project_slug"],
    )

    # ── webhook_deliveries ────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("delivery_id", sa.String(), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.Column("repo_name", sa.String(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── audit_events ──────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("repo_name", sa.String(), nullable=True),
        sa.Column("actor", sa.String(), nullable=False, server_default="slothops"),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
    op.create_index("ix_audit_events_repo_name", "audit_events", ["repo_name"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index(
        "ix_audit_workspace_created",
        "audit_events",
        ["workspace_id", "created_at"],
    )

    # ── rollbacks ─────────────────────────────────────────────────────────
    op.create_table(
        "rollbacks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("repo_name", sa.String(), nullable=False),
        sa.Column("failed_commit_sha", sa.String(), nullable=False),
        sa.Column("rolled_back_to_sha", sa.String(), nullable=True),
        sa.Column("backup_branch", sa.String(), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("pr_url", sa.String(), nullable=True),
        sa.Column("environment", sa.String(), nullable=True),
        sa.Column("deployment_ref", sa.String(), nullable=True),
        sa.Column("deployment_url", sa.String(), nullable=True),
        sa.Column("rollback_mode", sa.String(), nullable=False, server_default="approval_required"),
        sa.Column("rollback_strategy", sa.String(), nullable=False, server_default="rollback_pr"),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_reason", sa.String(), nullable=True),
        sa.Column("failure_reason", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "workspace_id", "repo_name", "failed_commit_sha",
            name="uq_rollback_sha"
        ),
    )
    op.create_index("ix_rollbacks_workspace_id", "rollbacks", ["workspace_id"])
    op.create_index("ix_rollbacks_repo_name", "rollbacks", ["repo_name"])
    op.create_index("ix_rollbacks_status", "rollbacks", ["status"])
    op.create_index(
        "ix_rollbacks_failed_sha",
        "rollbacks",
        ["workspace_id", "repo_name", "failed_commit_sha"],
    )

    # ── resolutions ───────────────────────────────────────────────────────
    op.create_table(
        "resolutions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("rollback_id", sa.String(), sa.ForeignKey("rollbacks.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("repo_name", sa.String(), nullable=False),
        sa.Column("backup_branch", sa.String(), nullable=False),
        sa.Column("resolution_pr_url", sa.String(), nullable=True),
        sa.Column("resolution_pr_number", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("build_error_log", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_resolutions_rollback_id", "resolutions", ["rollback_id"])
    op.create_index("ix_resolutions_workspace_id", "resolutions", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("resolutions")
    op.drop_table("rollbacks")
    op.drop_table("audit_events")
    op.drop_table("webhook_deliveries")
    op.drop_table("repo_configs")
    op.drop_table("qa_configs")
    op.drop_table("qa_reports")
    op.drop_table("issues")
    op.drop_table("developer_configs")
    op.drop_table("integrations")
    op.drop_table("workspace_users")
    op.drop_table("workspaces")
    op.drop_table("users")
