"""
SlothOps Engine — Production Rollback
Handles automatic revert of bad commits on main based on CI/CD deployment failures.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import subprocess
import uuid
from datetime import datetime

from app import database as db
from app.models import AuditAction, AuditEvent, RollbackMode, RollbackRecord, RollbackStatus, RollbackStrategy
from app.integrations.github_app import get_repo_for_installation
from app.policy import get_effective_policy
from app.sse_manager import broadcast
from app.integrations.email_sender import send_rollback_notification_email

logger = logging.getLogger("slothops.rollback")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
QA_EMAIL_RECIPIENT = os.getenv("QA_EMAIL_RECIPIENT", "")


async def plan_rollback(
    workspace_id: str,
    repo_name: str,
    failed_sha: str,
    github_app_id: int,
    github_app_private_key: str,
    db_path: str,
    failure_reason: str = "Production deployment failed",
    environment: str | None = None,
    deployment_ref: str | None = None,
    deployment_url: str | None = None,
):
    """Create a rollback record and queue execution only when policy allows it."""
    logger.info("Planning rollback for %s on %s", failed_sha[:8], repo_name)
    policy = await get_effective_policy(workspace_id, repo_name, db_path)
    mode = policy.get("rollback_mode", RollbackMode.APPROVAL_REQUIRED.value)
    strategy = policy.get("rollback_strategy", RollbackStrategy.ROLLBACK_PR.value)

    existing = await db.get_rollback_by_failed_sha(workspace_id, repo_name, failed_sha, db_path)
    if existing:
        logger.warning("Rollback for %s has already been planned. Skipping.", failed_sha[:8])
        return existing

    backup_branch = f"slothops/backup-{failed_sha[:8]}"
    rollback_id = str(uuid.uuid4())
    status = RollbackStatus.PENDING_APPROVAL.value
    if mode == RollbackMode.DISABLED.value:
        status = RollbackStatus.ABORTED.value

    record = RollbackRecord(
        id=rollback_id,
        workspace_id=workspace_id,
        repo_name=repo_name,
        failed_commit_sha=failed_sha,
        backup_branch=backup_branch,
        environment=environment,
        deployment_ref=deployment_ref,
        deployment_url=deployment_url,
        rollback_mode=mode,
        rollback_strategy=strategy,
        failure_reason=failure_reason,
        status=status,
    )
    await db.create_rollback(record, db_path)
    await db.create_audit_event(AuditEvent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        repo_name=repo_name,
        action=AuditAction.ROLLBACK_PLANNED.value,
        target_type="rollback",
        target_id=rollback_id,
        metadata_json={"failed_sha": failed_sha, "mode": mode, "strategy": strategy},
    ), db_path)
    await broadcast("rollback_event", record.model_dump())

    if mode == RollbackMode.AUTO_REVERT.value:
        asyncio.create_task(execute_rollback(rollback_id, workspace_id, github_app_id, github_app_private_key, db_path))
    return record


async def execute_rollback(
    rollback_id: str,
    workspace_id: str,
    github_app_id: int,
    github_app_private_key: str,
    db_path: str,
):
    """Execute an approved rollback using the configured strategy."""
    record = await db.get_rollback(rollback_id, db_path)
    if not record or record.workspace_id != workspace_id:
        return
    await db.update_rollback(rollback_id, db_path, status=RollbackStatus.REVERTING.value)
    record.status = RollbackStatus.REVERTING.value
    await broadcast("rollback_event", record.model_dump())

    integration_record = await db.get_integration(workspace_id, db_path)
    if not integration_record or not integration_record.github_installation_id:
        await db.update_rollback(rollback_id, db_path, status=RollbackStatus.FAILED.value, failure_reason="GitHub App not linked")
        await db.create_audit_event(AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            repo_name=record.repo_name,
            action=AuditAction.ROLLBACK_FAILED.value,
            target_type="rollback",
            target_id=rollback_id,
            metadata_json={"reason": "GitHub App not linked"},
        ), db_path)
        return

    try:
        repo, installation_auth = get_repo_for_installation(
            github_app_id,
            github_app_private_key,
            integration_record.github_installation_id,
            record.repo_name,
        )
    except Exception as e:
        logger.error("Failed to auth GitHub App for Rollback: %s", e)
        await db.update_rollback(rollback_id, db_path, status=RollbackStatus.FAILED.value, failure_reason=str(e))
        await db.create_audit_event(AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            repo_name=record.repo_name,
            action=AuditAction.ROLLBACK_FAILED.value,
            target_type="rollback",
            target_id=rollback_id,
            metadata_json={"reason": str(e)},
        ), db_path)
        return

    pr_number = None
    pr_url = None
    try:
        commit_obj = repo.get_commit(record.failed_commit_sha)
        is_merge = len(commit_obj.parents) > 1
        if commit_obj.commit.message.startswith("Revert"):
            await db.update_rollback(rollback_id, db_path, status=RollbackStatus.ABORTED.value, failure_reason="Commit is already a revert")
            await db.create_audit_event(AuditEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                repo_name=record.repo_name,
                action=AuditAction.ROLLBACK_ABORTED.value,
                target_type="rollback",
                target_id=rollback_id,
                metadata_json={"reason": "Commit is already a revert"},
            ), db_path)
            return
        prs = commit_obj.get_pulls()
        for p in prs:
            pr_number = p.number
            pr_url = p.html_url
            break
    except Exception as e:
        logger.warning("Could not find commit or PR info for %s: %s", record.failed_commit_sha[:8], e)
        is_merge = False

    clone_url = repo.clone_url.replace("https://", f"https://x-access-token:{installation_auth.token}@")
    revert_commit_sha = None

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.run(["git", "clone", clone_url, tmpdir], check=True, capture_output=True, timeout=60)
            subprocess.run(["git", "checkout", "main"], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "branch", record.backup_branch, record.failed_commit_sha], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", record.backup_branch], cwd=tmpdir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "bot@slothops.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "SlothOps Bot"], cwd=tmpdir)
            revert_cmd = ["git", "revert", "--no-edit"]
            if is_merge:
                revert_cmd.extend(["-m", "1"])
            revert_cmd.append(record.failed_commit_sha)
            res = subprocess.run(revert_cmd, cwd=tmpdir, capture_output=True, text=True)
            if res.returncode != 0:
                raise Exception(f"Git revert failed: {res.stderr}")

            rev_parse = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmpdir, capture_output=True, text=True)
            revert_commit_sha = rev_parse.stdout.strip()
            if record.rollback_strategy == RollbackStrategy.DIRECT_REVERT.value:
                subprocess.run(["git", "push", "origin", "main"], cwd=tmpdir, check=True, capture_output=True)
            else:
                rollback_branch = f"slothops/rollback-{record.failed_commit_sha[:8]}"
                subprocess.run(["git", "checkout", "-b", rollback_branch], cwd=tmpdir, check=True, capture_output=True)
                subprocess.run(["git", "push", "origin", rollback_branch], cwd=tmpdir, check=True, capture_output=True)
                pr = repo.create_pull(
                    title=f"revert: rollback failed deployment {record.failed_commit_sha[:8]}",
                    body=f"SlothOps prepared this rollback after deployment failure.\n\nReason: {record.failure_reason}",
                    head=rollback_branch,
                    base="main",
                    draft=False,
                )
                pr_url = pr.html_url
                pr_number = pr.number
        except Exception as e:
            logger.error("Sandbox rollback logic failed: %s", e)
            await db.update_rollback(rollback_id, db_path, status=RollbackStatus.FAILED.value, failure_reason=f"{record.failure_reason} (Revert script failed: {e})")
            await db.create_audit_event(AuditEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                repo_name=record.repo_name,
                action=AuditAction.ROLLBACK_FAILED.value,
                target_type="rollback",
                target_id=rollback_id,
                metadata_json={"reason": str(e)},
            ), db_path)
            record.status = RollbackStatus.FAILED.value
            await broadcast("rollback_event", record.model_dump())
            return

    final_status = RollbackStatus.COMPLETED.value if record.rollback_strategy == RollbackStrategy.DIRECT_REVERT.value else RollbackStatus.ROLLBACK_PR_OPENED.value
    await db.update_rollback(
        rollback_id,
        db_path,
        status=final_status,
        rolled_back_to_sha=revert_commit_sha,
        pr_number=pr_number,
        pr_url=pr_url,
    )
    record.status = final_status
    record.rolled_back_to_sha = revert_commit_sha
    record.pr_number = pr_number
    record.pr_url = pr_url
    await broadcast("rollback_event", record.model_dump())
    await db.create_audit_event(AuditEvent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        repo_name=record.repo_name,
        action=AuditAction.ROLLBACK_EXECUTED.value,
        target_type="rollback",
        target_id=rollback_id,
        metadata_json={
            "status": final_status,
            "strategy": record.rollback_strategy,
            "revert_commit_sha": revert_commit_sha,
            "pr_url": pr_url,
        },
    ), db_path)

    # Comment on PR
    if pr_number:
        try:
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(
                f"🚨 **Production Deployment Failed**\n\n"
                f"SlothOps intercepted a deployment failure linked to this PR (`{record.failed_commit_sha[:8]}`).\n"
                f"A rollback was prepared using strategy `{record.rollback_strategy}`.\n\n"
                f"A backup branch preserving these changes has been created: `{record.backup_branch}`.\n"
                f"Please fix the build issues on the backup branch and open a new PR."
            )
            logger.info("Commented rollback notification on PR #%d", pr_number)
        except Exception as e:
            logger.warning("Could not comment on PR for rollback: %s", e)

    # Email
    if QA_EMAIL_RECIPIENT and SMTP_HOST:
        send_rollback_notification_email({
            "repo_name": record.repo_name,
            "failed_sha": record.failed_commit_sha[:8],
            "backup_branch": record.backup_branch,
            "pr_url": pr_url,
            "failure_reason": record.failure_reason
        }, QA_EMAIL_RECIPIENT, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD)

    # Trigger Resolution Auto-Fix
    from app.pipelines.resolution import attempt_resolution
    asyncio.create_task(attempt_resolution(
        rollback_id=rollback_id,
        workspace_id=workspace_id,
        repo_name=record.repo_name,
        backup_branch=record.backup_branch,
        build_error_log=record.failure_reason,
        failed_sha=record.failed_commit_sha,
        github_app_id=github_app_id,
        github_app_private_key=github_app_private_key,
        db_path=db_path,
        smtp_config={
            "SMTP_HOST": SMTP_HOST,
            "SMTP_PORT": SMTP_PORT,
            "SMTP_USER": SMTP_USER,
            "SMTP_PASSWORD": SMTP_PASSWORD,
            "QA_EMAIL_RECIPIENT": QA_EMAIL_RECIPIENT
        }
    ))


async def perform_rollback(*args, **kwargs):
    """Backward-compatible wrapper: plan rollback; execution now depends on policy/approval."""
    return await plan_rollback(*args, **kwargs)
