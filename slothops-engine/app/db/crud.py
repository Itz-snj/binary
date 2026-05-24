"""
SlothOps Engine — Database CRUD Operations
All persistence logic using SQLModel AsyncSession.
Call sites should use database.py facade which wraps these functions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import (
    AuditEventTable,
    DeveloperConfigTable,
    IntegrationTable,
    IssueTable,
    QAConfigTable,
    QAReportTable,
    RepoConfigTable,
    ResolutionTable,
    RollbackTable,
    UserTable,
    WebhookDeliveryTable,
    WorkspaceTable,
    WorkspaceUserTable,
)
from models import (
    AuditEvent,
    Integration,
    IssueRecord,
    QAReport,
    RepoConfig,
    ResolutionRecord,
    RollbackRecord,
    RollbackStatus,
    User,
    Workspace,
)

logger = logging.getLogger("slothops.db.crud")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Converters: ORM row → Pydantic model
# ─────────────────────────────────────────────────────────────────────────────

def _issue_row_to_model(row: IssueTable) -> IssueRecord:
    d = row.model_dump()
    # raw_payload stored as JSONB dict; IssueRecord expects Optional[str]
    raw = d.get("raw_payload")
    if isinstance(raw, dict):
        d["raw_payload"] = json.dumps(raw)
    return IssueRecord(**d)


def _repo_config_row_to_model(row: RepoConfigTable) -> RepoConfig:
    return RepoConfig(
        workspace_id=row.workspace_id,
        repo_name=row.repo_name,
        config_json=row.config_json or {},
        sentry_project_slug=row.sentry_project_slug,
        active=row.active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _rollback_row_to_model(row: RollbackTable) -> RollbackRecord:
    return RollbackRecord(**row.model_dump())


def _resolution_row_to_model(row: ResolutionTable) -> ResolutionRecord:
    return ResolutionRecord(**row.model_dump())


def _qa_report_row_to_model(row: QAReportTable) -> QAReport:
    return QAReport(**row.model_dump())


# ─────────────────────────────────────────────────────────────────────────────
# Issues
# ─────────────────────────────────────────────────────────────────────────────

async def create_issue(session: AsyncSession, issue: IssueRecord) -> None:
    raw_payload = None
    if issue.raw_payload:
        try:
            raw_payload = json.loads(issue.raw_payload)
        except (TypeError, json.JSONDecodeError):
            raw_payload = {"raw": issue.raw_payload}

    row = IssueTable(
        id=issue.id,
        workspace_id=issue.workspace_id,
        repo_name=issue.repo_name,
        fingerprint=issue.fingerprint,
        error_type=issue.error_type,
        error_message=issue.error_message,
        file_path=issue.file_path,
        function_name=issue.function_name,
        line_number=issue.line_number,
        stack_trace=issue.stack_trace,
        raw_payload=raw_payload,
        occurrence_count=issue.occurrence_count,
        classification=issue.classification,
        confidence=issue.confidence,
        status=issue.status,
        fix_pr_url=issue.fix_pr_url,
        fix_pr_branch=issue.fix_pr_branch,
        root_cause=issue.root_cause,
        recommendation=issue.recommendation,
        previous_fix_id=issue.previous_fix_id,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )
    session.add(row)
    await session.flush()


async def get_issue(
    session: AsyncSession, issue_id: str, workspace_id: str
) -> Optional[IssueRecord]:
    result = await session.exec(
        select(IssueTable).where(
            IssueTable.id == issue_id,
            IssueTable.workspace_id == workspace_id,
        )
    )
    row = result.first()
    return _issue_row_to_model(row) if row else None


async def get_issue_by_fingerprint(
    session: AsyncSession, fingerprint: str, workspace_id: str
) -> Optional[IssueRecord]:
    result = await session.exec(
        select(IssueTable)
        .where(
            IssueTable.fingerprint == fingerprint,
            IssueTable.workspace_id == workspace_id,
        )
        .order_by(IssueTable.created_at.desc())
        .limit(1)
    )
    row = result.first()
    return _issue_row_to_model(row) if row else None


async def update_issue_status(
    session: AsyncSession, issue_id: str, **kwargs
) -> None:
    result = await session.exec(
        select(IssueTable).where(IssueTable.id == issue_id)
    )
    row = result.first()
    if not row:
        return
    for k, v in kwargs.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = _now()
    session.add(row)
    await session.flush()


async def increment_occurrence(
    session: AsyncSession, issue_id: str, workspace_id: str
) -> None:
    result = await session.exec(
        select(IssueTable).where(
            IssueTable.id == issue_id,
            IssueTable.workspace_id == workspace_id,
        )
    )
    row = result.first()
    if row:
        row.occurrence_count += 1
        row.updated_at = _now()
        session.add(row)
        await session.flush()


async def list_issues(
    session: AsyncSession, workspace_id: str
) -> list[IssueRecord]:
    result = await session.exec(
        select(IssueTable)
        .where(IssueTable.workspace_id == workspace_id)
        .order_by(IssueTable.created_at.desc())
    )
    return [_issue_row_to_model(r) for r in result.all()]


# ─────────────────────────────────────────────────────────────────────────────
# Users & Auth
# ─────────────────────────────────────────────────────────────────────────────

async def create_user(session: AsyncSession, user: User) -> None:
    row = UserTable(
        id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
        created_at=user.created_at,
    )
    session.add(row)
    await session.flush()


async def get_user_by_email(
    session: AsyncSession, email: str
) -> Optional[User]:
    result = await session.exec(
        select(UserTable).where(UserTable.email == email)
    )
    row = result.first()
    if not row:
        return None
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        created_at=row.created_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Workspaces
# ─────────────────────────────────────────────────────────────────────────────

async def create_workspace(session: AsyncSession, workspace: Workspace) -> None:
    row = WorkspaceTable(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at,
    )
    session.add(row)
    await session.flush()


async def add_user_to_workspace(
    session: AsyncSession, workspace_id: str, user_id: str, role: str = "admin"
) -> None:
    row = WorkspaceUserTable(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )
    session.add(row)
    await session.flush()


async def get_user_workspaces(
    session: AsyncSession, user_id: str
) -> list[Workspace]:
    result = await session.exec(
        select(WorkspaceTable)
        .join(
            WorkspaceUserTable,
            WorkspaceTable.id == WorkspaceUserTable.workspace_id,
        )
        .where(WorkspaceUserTable.user_id == user_id)
    )
    return [
        Workspace(id=r.id, name=r.name, created_at=r.created_at)
        for r in result.all()
    ]


async def list_workspaces(session: AsyncSession) -> list[Workspace]:
    result = await session.exec(select(WorkspaceTable))
    return [
        Workspace(id=r.id, name=r.name, created_at=r.created_at)
        for r in result.all()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Integrations
# ─────────────────────────────────────────────────────────────────────────────

async def get_integration(
    session: AsyncSession, workspace_id: str
) -> Optional[Integration]:
    result = await session.exec(
        select(IntegrationTable).where(
            IntegrationTable.workspace_id == workspace_id
        )
    )
    row = result.first()
    if not row:
        return None
    return Integration(
        workspace_id=row.workspace_id,
        github_installation_id=row.github_installation_id,
        sentry_webhook_secret=row.sentry_webhook_secret,
    )


async def upsert_integration(
    session: AsyncSession, integration: Integration
) -> None:
    result = await session.exec(
        select(IntegrationTable).where(
            IntegrationTable.workspace_id == integration.workspace_id
        )
    )
    row = result.first()
    if row:
        row.github_installation_id = integration.github_installation_id
        row.sentry_webhook_secret = integration.sentry_webhook_secret
    else:
        row = IntegrationTable(
            workspace_id=integration.workspace_id,
            github_installation_id=integration.github_installation_id,
            sentry_webhook_secret=integration.sentry_webhook_secret,
        )
    session.add(row)
    await session.flush()


async def get_workspace_by_installation_id(
    session: AsyncSession, installation_id: str
) -> Optional[str]:
    result = await session.exec(
        select(IntegrationTable).where(
            IntegrationTable.github_installation_id == str(installation_id)
        )
    )
    row = result.first()
    return row.workspace_id if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Repo Configs
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_repo_config(
    session: AsyncSession, config: RepoConfig
) -> None:
    result = await session.exec(
        select(RepoConfigTable).where(
            RepoConfigTable.workspace_id == config.workspace_id,
            RepoConfigTable.repo_name == config.repo_name,
        )
    )
    row = result.first()
    if row:
        row.config_json = config.config_json
        row.sentry_project_slug = config.sentry_project_slug
        row.active = config.active
        row.updated_at = _now()
    else:
        row = RepoConfigTable(
            workspace_id=config.workspace_id,
            repo_name=config.repo_name,
            config_json=config.config_json,
            sentry_project_slug=config.sentry_project_slug,
            active=config.active,
            created_at=config.created_at,
            updated_at=_now(),
        )
    session.add(row)
    await session.flush()


async def get_repo_config(
    session: AsyncSession, workspace_id: str, repo_name: str
) -> Optional[RepoConfig]:
    result = await session.exec(
        select(RepoConfigTable).where(
            RepoConfigTable.workspace_id == workspace_id,
            RepoConfigTable.repo_name == repo_name,
        )
    )
    row = result.first()
    return _repo_config_row_to_model(row) if row else None


async def get_active_repo_config(
    session: AsyncSession, workspace_id: str
) -> Optional[RepoConfig]:
    result = await session.exec(
        select(RepoConfigTable)
        .where(
            RepoConfigTable.workspace_id == workspace_id,
            RepoConfigTable.active == True,  # noqa: E712
        )
        .order_by(RepoConfigTable.updated_at.desc())
        .limit(1)
    )
    row = result.first()
    return _repo_config_row_to_model(row) if row else None


async def get_repo_config_by_sentry_project(
    session: AsyncSession, workspace_id: str, sentry_project_slug: str
) -> Optional[RepoConfig]:
    result = await session.exec(
        select(RepoConfigTable)
        .where(
            RepoConfigTable.workspace_id == workspace_id,
            RepoConfigTable.sentry_project_slug == sentry_project_slug,
            RepoConfigTable.active == True,  # noqa: E712
        )
        .order_by(RepoConfigTable.updated_at.desc())
        .limit(1)
    )
    row = result.first()
    return _repo_config_row_to_model(row) if row else None


async def list_repo_configs(
    session: AsyncSession, workspace_id: str
) -> list[RepoConfig]:
    result = await session.exec(
        select(RepoConfigTable).where(
            RepoConfigTable.workspace_id == workspace_id
        )
    )
    return [_repo_config_row_to_model(r) for r in result.all()]


# ─────────────────────────────────────────────────────────────────────────────
# Developer Config
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_developer_config(
    session: AsyncSession, workspace_id: str, config_json: str
) -> None:
    try:
        config_dict = json.loads(config_json)
    except (TypeError, json.JSONDecodeError):
        config_dict = {}

    result = await session.exec(
        select(DeveloperConfigTable).where(
            DeveloperConfigTable.workspace_id == workspace_id
        )
    )
    row = result.first()
    if row:
        row.config_json = config_dict
        row.updated_at = _now()
    else:
        row = DeveloperConfigTable(
            workspace_id=workspace_id,
            config_json=config_dict,
            updated_at=_now(),
        )
    session.add(row)
    await session.flush()


async def get_developer_config(
    session: AsyncSession, workspace_id: str
) -> Optional[dict]:
    result = await session.exec(
        select(DeveloperConfigTable).where(
            DeveloperConfigTable.workspace_id == workspace_id
        )
    )
    row = result.first()
    return row.config_json if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Webhook Deliveries
# ─────────────────────────────────────────────────────────────────────────────

async def record_webhook_delivery(
    session: AsyncSession,
    delivery_id: str,
    event_type: str,
    workspace_id: Optional[str],
    repo_name: Optional[str],
) -> bool:
    """Insert delivery record. Returns False if already seen (duplicate)."""
    if not delivery_id:
        return True
    try:
        row = WebhookDeliveryTable(
            delivery_id=delivery_id,
            event_type=event_type,
            workspace_id=workspace_id,
            repo_name=repo_name,
            received_at=_now(),
        )
        session.add(row)
        await session.flush()
        return True
    except IntegrityError:
        await session.rollback()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Audit Events
# ─────────────────────────────────────────────────────────────────────────────

async def create_audit_event(
    session: AsyncSession, event: AuditEvent
) -> None:
    row = AuditEventTable(
        id=event.id,
        workspace_id=event.workspace_id,
        repo_name=event.repo_name,
        actor=event.actor,
        action=event.action,
        target_type=event.target_type,
        target_id=event.target_id,
        metadata_json=event.metadata_json,
        created_at=event.created_at,
    )
    session.add(row)
    await session.flush()


async def list_audit_events(
    session: AsyncSession,
    workspace_id: str,
    repo_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
) -> list[AuditEvent]:
    stmt = select(AuditEventTable).where(
        AuditEventTable.workspace_id == workspace_id
    )
    if repo_name:
        stmt = stmt.where(AuditEventTable.repo_name == repo_name)
    if action:
        stmt = stmt.where(AuditEventTable.action == action)
    stmt = stmt.order_by(AuditEventTable.created_at.desc()).limit(limit)
    result = await session.exec(stmt)
    return [
        AuditEvent(
            id=r.id,
            workspace_id=r.workspace_id,
            repo_name=r.repo_name,
            actor=r.actor,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            metadata_json=r.metadata_json or {},
            created_at=r.created_at,
        )
        for r in result.all()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# QA Reports
# ─────────────────────────────────────────────────────────────────────────────

async def create_qa_report(session: AsyncSession, report: QAReport) -> None:
    row = QAReportTable(
        id=report.id,
        workspace_id=report.workspace_id,
        pr_number=report.pr_number,
        pr_url=report.pr_url,
        commit_sha=report.commit_sha,
        repo_name=report.repo_name,
        static_analysis=report.static_analysis,
        functionality=report.functionality,
        stress_test=report.stress_test,
        vapt=report.vapt,
        regression=report.regression,
        performance=report.performance,
        triage=report.triage,
        required_agents=report.required_agents,
        advisory_agents=report.advisory_agents,
        artifacts=report.artifacts,
        overall_status=report.overall_status,
        summary=report.summary,
        email_sent_to=report.email_sent_to,
        email_sent_at=report.email_sent_at,
        created_at=report.created_at,
    )
    session.add(row)
    await session.flush()


async def update_qa_report(
    session: AsyncSession, report_id: str, **kwargs
) -> None:
    result = await session.exec(
        select(QAReportTable).where(QAReportTable.id == report_id)
    )
    row = result.first()
    if not row:
        return
    for k, v in kwargs.items():
        if hasattr(row, k):
            setattr(row, k, v)
    session.add(row)
    await session.flush()


async def get_qa_reports(
    session: AsyncSession, workspace_id: str
) -> list[QAReport]:
    result = await session.exec(
        select(QAReportTable)
        .where(QAReportTable.workspace_id == workspace_id)
        .order_by(QAReportTable.created_at.desc())
    )
    return [_qa_report_row_to_model(r) for r in result.all()]


async def get_qa_report(
    session: AsyncSession, report_id: str
) -> Optional[QAReport]:
    result = await session.exec(
        select(QAReportTable).where(QAReportTable.id == report_id)
    )
    row = result.first()
    return _qa_report_row_to_model(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Rollbacks
# ─────────────────────────────────────────────────────────────────────────────

async def create_rollback(session: AsyncSession, record: RollbackRecord) -> None:
    row = RollbackTable(**record.model_dump())
    session.add(row)
    await session.flush()


async def update_rollback(
    session: AsyncSession, rollback_id: str, **kwargs
) -> None:
    result = await session.exec(
        select(RollbackTable).where(RollbackTable.id == rollback_id)
    )
    row = result.first()
    if not row:
        return
    for k, v in kwargs.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = _now()
    session.add(row)
    await session.flush()


async def get_rollbacks(
    session: AsyncSession, workspace_id: str
) -> list[RollbackRecord]:
    result = await session.exec(
        select(RollbackTable)
        .where(RollbackTable.workspace_id == workspace_id)
        .order_by(RollbackTable.created_at.desc())
    )
    return [_rollback_row_to_model(r) for r in result.all()]


async def get_rollback(
    session: AsyncSession, rollback_id: str
) -> Optional[RollbackRecord]:
    result = await session.exec(
        select(RollbackTable).where(RollbackTable.id == rollback_id)
    )
    row = result.first()
    return _rollback_row_to_model(row) if row else None


async def get_rollback_by_backup_branch(
    session: AsyncSession, backup_branch: str
) -> Optional[RollbackRecord]:
    result = await session.exec(
        select(RollbackTable).where(RollbackTable.backup_branch == backup_branch)
    )
    row = result.first()
    return _rollback_row_to_model(row) if row else None


async def get_rollback_by_failed_sha(
    session: AsyncSession, workspace_id: str, repo_name: str, sha: str
) -> Optional[RollbackRecord]:
    result = await session.exec(
        select(RollbackTable)
        .where(
            RollbackTable.workspace_id == workspace_id,
            RollbackTable.repo_name == repo_name,
            RollbackTable.failed_commit_sha == sha,
        )
        .order_by(RollbackTable.created_at.desc())
        .limit(1)
    )
    row = result.first()
    return _rollback_row_to_model(row) if row else None


async def approve_rollback(
    session: AsyncSession,
    rollback_id: str,
    approved_by: str,
    reason: str,
) -> None:
    await update_rollback(
        session,
        rollback_id,
        status=RollbackStatus.APPROVED.value,
        approved_by=approved_by,
        approved_at=_now(),
        approval_reason=reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Resolutions
# ─────────────────────────────────────────────────────────────────────────────

async def create_resolution(
    session: AsyncSession, record: ResolutionRecord
) -> None:
    row = ResolutionTable(**record.model_dump())
    session.add(row)
    await session.flush()


async def update_resolution(
    session: AsyncSession, resolution_id: str, **kwargs
) -> None:
    result = await session.exec(
        select(ResolutionTable).where(ResolutionTable.id == resolution_id)
    )
    row = result.first()
    if not row:
        return
    for k, v in kwargs.items():
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = _now()
    session.add(row)
    await session.flush()


async def get_resolutions_for_rollback(
    session: AsyncSession, rollback_id: str
) -> list[ResolutionRecord]:
    result = await session.exec(
        select(ResolutionTable)
        .where(ResolutionTable.rollback_id == rollback_id)
        .order_by(ResolutionTable.attempt_number.desc())
    )
    return [_resolution_row_to_model(r) for r in result.all()]


async def get_resolution(
    session: AsyncSession, resolution_id: str
) -> Optional[ResolutionRecord]:
    result = await session.exec(
        select(ResolutionTable).where(ResolutionTable.id == resolution_id)
    )
    row = result.first()
    return _resolution_row_to_model(row) if row else None
