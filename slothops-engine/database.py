"""
SlothOps Engine — Database Compatibility Facade
Maintains the original function signatures used by main.py, pipeline.py,
qa_pipeline.py, rollback.py, resolution.py, and fingerprint.py.

All functions delegate to db/crud.py via a fresh AsyncSession.
The `db_path` parameter is accepted but ignored (legacy SQLite artifact).
Callers do NOT need to change.
"""

from __future__ import annotations

import logging
from typing import Optional

from db.engine import async_session_factory
import db.crud as _crud
from models import (
    AuditEvent,
    Integration,
    IssueRecord,
    QAReport,
    RepoConfig,
    ResolutionRecord,
    RollbackRecord,
    User,
    Workspace,
)

logger = logging.getLogger("slothops.database")

_LEGACY_WARNING_SHOWN = False


def _warn_db_path(db_path: str) -> None:
    global _LEGACY_WARNING_SHOWN
    if not _LEGACY_WARNING_SHOWN and db_path and db_path != "./slothops.db":
        logger.warning(
            "database.py: db_path=%r is ignored. All operations target PostgreSQL via DATABASE_URL.",
            db_path,
        )
        _LEGACY_WARNING_SHOWN = True


# ── Init (no-op — Alembic handles schema) ───────────────────────────────

async def init_db(db_path: str = "./slothops.db") -> None:
    """No-op: schema is managed by Alembic migrations."""
    _warn_db_path(db_path)
    logger.info("init_db() called — schema managed by Alembic, skipping.")


# ── Issues ───────────────────────────────────────────────────────────────

async def create_issue(issue: IssueRecord, db_path: str = "./slothops.db") -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_issue(session, issue)
        await session.commit()


async def get_issue(
    issue_id: str, workspace_id: str, db_path: str = "./slothops.db"
) -> Optional[IssueRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_issue(session, issue_id, workspace_id)


async def get_issue_by_fingerprint(
    fingerprint: str, workspace_id: str, db_path: str = "./slothops.db"
) -> Optional[IssueRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_issue_by_fingerprint(session, fingerprint, workspace_id)


async def update_issue_status(
    issue_id: str, db_path: str = "./slothops.db", **kwargs
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.update_issue_status(session, issue_id, **kwargs)
        await session.commit()


async def increment_occurrence(
    issue_id: str, workspace_id: str, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.increment_occurrence(session, issue_id, workspace_id)
        await session.commit()


async def list_issues(
    workspace_id: str, db_path: str = "./slothops.db"
) -> list[IssueRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.list_issues(session, workspace_id)


# ── Users & Auth ─────────────────────────────────────────────────────────

async def create_user(user: User, db_path: str = "./slothops.db") -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_user(session, user)
        await session.commit()


async def get_user_by_email(
    email: str, db_path: str = "./slothops.db"
) -> Optional[User]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_user_by_email(session, email)


# ── Workspaces ───────────────────────────────────────────────────────────

async def create_workspace(
    workspace: Workspace, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_workspace(session, workspace)
        await session.commit()


async def add_user_to_workspace(
    workspace_id: str,
    user_id: str,
    role: str = "admin",
    db_path: str = "./slothops.db",
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.add_user_to_workspace(session, workspace_id, user_id, role)
        await session.commit()


async def get_user_workspaces(
    user_id: str, db_path: str = "./slothops.db"
) -> list[Workspace]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_user_workspaces(session, user_id)


async def list_workspaces(db_path: str = "./slothops.db") -> list[Workspace]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.list_workspaces(session)


# ── Integrations ─────────────────────────────────────────────────────────

async def get_integration(
    workspace_id: str, db_path: str = "./slothops.db"
) -> Optional[Integration]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_integration(session, workspace_id)


async def upsert_integration(
    integration: Integration, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.upsert_integration(session, integration)
        await session.commit()


async def get_workspace_by_installation_id(
    installation_id: str, db_path: str = "./slothops.db"
) -> Optional[str]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_workspace_by_installation_id(session, installation_id)


# ── Repo Configs ─────────────────────────────────────────────────────────

async def upsert_repo_config(
    config: RepoConfig, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.upsert_repo_config(session, config)
        await session.commit()


async def get_repo_config(
    workspace_id: str, repo_name: str, db_path: str = "./slothops.db"
) -> Optional[RepoConfig]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_repo_config(session, workspace_id, repo_name)


async def get_active_repo_config(
    workspace_id: str, db_path: str = "./slothops.db"
) -> Optional[RepoConfig]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_active_repo_config(session, workspace_id)


async def get_repo_config_by_sentry_project(
    workspace_id: str,
    sentry_project_slug: str,
    db_path: str = "./slothops.db",
) -> Optional[RepoConfig]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_repo_config_by_sentry_project(
            session, workspace_id, sentry_project_slug
        )


async def list_repo_configs(
    workspace_id: str, db_path: str = "./slothops.db"
) -> list[RepoConfig]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.list_repo_configs(session, workspace_id)


# ── Developer Config ─────────────────────────────────────────────────────

async def upsert_developer_config(
    workspace_id: str, config_json: str, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.upsert_developer_config(session, workspace_id, config_json)
        await session.commit()


async def get_developer_config(
    workspace_id: str, db_path: str = "./slothops.db"
) -> Optional[dict]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_developer_config(session, workspace_id)


# ── Webhook Deliveries ────────────────────────────────────────────────────

async def record_webhook_delivery(
    delivery_id: str,
    event_type: str,
    workspace_id: Optional[str],
    repo_name: Optional[str],
    db_path: str = "./slothops.db",
) -> bool:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        result = await _crud.record_webhook_delivery(
            session, delivery_id, event_type, workspace_id, repo_name
        )
        if result:
            await session.commit()
        return result


# ── Audit Events ─────────────────────────────────────────────────────────

async def create_audit_event(
    event: AuditEvent, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_audit_event(session, event)
        await session.commit()


async def list_audit_events(
    workspace_id: str,
    repo_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    db_path: str = "./slothops.db",
) -> list[AuditEvent]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.list_audit_events(
            session, workspace_id, repo_name, action, limit
        )


# ── QA Reports ───────────────────────────────────────────────────────────

async def create_qa_report(
    report: QAReport, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_qa_report(session, report)
        await session.commit()


async def update_qa_report(
    report_id: str, db_path: str = "./slothops.db", **kwargs
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.update_qa_report(session, report_id, **kwargs)
        await session.commit()


async def get_qa_reports(
    workspace_id: str, db_path: str = "./slothops.db"
) -> list[QAReport]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_qa_reports(session, workspace_id)


async def get_qa_report(
    report_id: str, db_path: str = "./slothops.db"
) -> Optional[QAReport]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_qa_report(session, report_id)


# ── Rollbacks ────────────────────────────────────────────────────────────

async def create_rollback(
    record: RollbackRecord, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_rollback(session, record)
        await session.commit()


async def update_rollback(
    rollback_id: str, db_path: str = "./slothops.db", **kwargs
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.update_rollback(session, rollback_id, **kwargs)
        await session.commit()


async def get_rollbacks(
    workspace_id: str, db_path: str = "./slothops.db"
) -> list[RollbackRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_rollbacks(session, workspace_id)


async def get_rollback(
    rollback_id: str, db_path: str = "./slothops.db"
) -> Optional[RollbackRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_rollback(session, rollback_id)


async def get_rollback_by_backup_branch(
    backup_branch: str, db_path: str = "./slothops.db"
) -> Optional[RollbackRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_rollback_by_backup_branch(session, backup_branch)


async def get_rollback_by_failed_sha(
    workspace_id: str,
    repo_name: str,
    sha: str,
    db_path: str = "./slothops.db",
) -> Optional[RollbackRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_rollback_by_failed_sha(
            session, workspace_id, repo_name, sha
        )


async def approve_rollback(
    rollback_id: str,
    approved_by: str,
    reason: str,
    db_path: str = "./slothops.db",
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.approve_rollback(session, rollback_id, approved_by, reason)
        await session.commit()


# ── Resolutions ───────────────────────────────────────────────────────────

async def create_resolution(
    record: ResolutionRecord, db_path: str = "./slothops.db"
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.create_resolution(session, record)
        await session.commit()


async def update_resolution(
    resolution_id: str, db_path: str = "./slothops.db", **kwargs
) -> None:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        await _crud.update_resolution(session, resolution_id, **kwargs)
        await session.commit()


async def get_resolutions_for_rollback(
    rollback_id: str, db_path: str = "./slothops.db"
) -> list[ResolutionRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_resolutions_for_rollback(session, rollback_id)


async def get_resolution(
    resolution_id: str, db_path: str = "./slothops.db"
) -> Optional[ResolutionRecord]:
    _warn_db_path(db_path)
    async with async_session_factory() as session:
        return await _crud.get_resolution(session, resolution_id)
