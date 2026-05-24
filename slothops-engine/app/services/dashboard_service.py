"""Dashboard data aggregation service.

Routers in app.api.dashboard delegate here. Functions return dashboard
view models (app.schemas.dashboard) rather than raw DB rows.
"""

from __future__ import annotations

import logging
import os
from collections import Counter

from app import database as db
from app.schemas.dashboard import (
    DashboardActivityItem,
    DashboardHealthStatus,
    DashboardMetric,
    DashboardOverview,
    DashboardRepoCard,
)
from app.models import IssueStatus, QAStatus, RollbackStatus

logger = logging.getLogger("slothops.services.dashboard")


async def build_repo_cards(workspace_id: str, db_path: str) -> list[DashboardRepoCard]:
    repo_configs = await db.list_repo_configs(workspace_id, db_path)
    qa_reports = await db.get_qa_reports(workspace_id, db_path)
    rollbacks = await db.get_rollbacks(workspace_id, db_path)
    issues = await db.list_issues(workspace_id, db_path)

    latest_qa_by_repo: dict[str, str] = {}
    for r in sorted(qa_reports, key=lambda x: x.created_at):
        if r.repo_name:
            latest_qa_by_repo[r.repo_name] = r.overall_status

    latest_rb_by_repo: dict[str, str] = {}
    for r in sorted(rollbacks, key=lambda x: x.created_at):
        if r.repo_name:
            latest_rb_by_repo[r.repo_name] = r.status

    open_issue_statuses = {
        IssueStatus.RECEIVED.value,
        IssueStatus.TRIAGING.value,
        IssueStatus.CLASSIFIED.value,
        IssueStatus.FIXING.value,
        IssueStatus.PR_CREATED.value,
    }
    open_count_by_repo: Counter[str] = Counter()
    for i in issues:
        if i.repo_name and i.status in open_issue_statuses:
            open_count_by_repo[i.repo_name] += 1

    cards: list[DashboardRepoCard] = []
    for rc in repo_configs:
        cards.append(DashboardRepoCard(
            repo_name=rc.repo_name,
            active=rc.active,
            sentry_project_slug=rc.sentry_project_slug,
            last_qa_status=latest_qa_by_repo.get(rc.repo_name),
            last_rollback_status=latest_rb_by_repo.get(rc.repo_name),
            open_issues=open_count_by_repo.get(rc.repo_name, 0),
        ))
    cards.sort(key=lambda c: (not c.active, c.repo_name))
    return cards


async def build_activity(
    workspace_id: str, db_path: str, limit: int = 20,
) -> list[DashboardActivityItem]:
    events = await db.list_audit_events(workspace_id, limit=limit, db_path=db_path)
    return [
        DashboardActivityItem(
            ts=e.created_at,
            actor=e.actor,
            action=e.action,
            target_type=e.target_type,
            target_id=e.target_id,
            metadata=e.metadata_json or {},
        )
        for e in events
    ]


async def build_metrics(workspace_id: str, db_path: str) -> list[DashboardMetric]:
    issues = await db.list_issues(workspace_id, db_path)
    qa_reports = await db.get_qa_reports(workspace_id, db_path)
    rollbacks = await db.get_rollbacks(workspace_id, db_path)

    open_issue_statuses = {
        IssueStatus.RECEIVED.value,
        IssueStatus.TRIAGING.value,
        IssueStatus.CLASSIFIED.value,
        IssueStatus.FIXING.value,
        IssueStatus.PR_CREATED.value,
    }
    open_issues = sum(1 for i in issues if i.status in open_issue_statuses)
    prs_created = sum(
        1 for i in issues
        if i.status in (IssueStatus.PR_CREATED.value, IssueStatus.PR_MERGED.value)
    )
    qa_failed = sum(1 for r in qa_reports if r.overall_status == QAStatus.FAILED.value)
    rollbacks_pending = sum(
        1 for r in rollbacks
        if r.status in (
            RollbackStatus.PENDING.value,
            RollbackStatus.PENDING_APPROVAL.value,
        )
    )

    return [
        DashboardMetric(name="open_issues", value=float(open_issues)),
        DashboardMetric(name="prs_created", value=float(prs_created)),
        DashboardMetric(name="qa_failed", value=float(qa_failed)),
        DashboardMetric(name="rollbacks_pending", value=float(rollbacks_pending)),
        DashboardMetric(name="total_issues", value=float(len(issues))),
    ]


async def build_health(workspace_id: str, db_path: str) -> DashboardHealthStatus:
    """Best-effort health snapshot. Each probe is independent — a failure
    on one component leaves the others reportable.
    """
    integration = None
    try:
        integration = await db.get_integration(workspace_id, db_path)
        database_status = "ok"
    except Exception as e:
        logger.warning("DB health probe failed for %s: %s", workspace_id, e)
        database_status = "error"

    github_status = "linked" if integration and integration.github_installation_id else "unlinked"
    sentry_status = "linked" if integration and integration.sentry_webhook_secret else "unlinked"

    llm_status = "configured" if (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    ) else "unconfigured"

    return DashboardHealthStatus(
        github=github_status,
        sentry=sentry_status,
        llm=llm_status,
        database=database_status,
    )


async def build_overview(workspace_id: str, db_path: str) -> DashboardOverview:
    metrics = await build_metrics(workspace_id, db_path)
    repos = await build_repo_cards(workspace_id, db_path)
    activity = await build_activity(workspace_id, db_path, limit=20)
    health = await build_health(workspace_id, db_path)
    return DashboardOverview(
        workspace_id=workspace_id,
        metrics=metrics,
        repos=repos,
        recent_activity=activity,
        health=health,
    )
