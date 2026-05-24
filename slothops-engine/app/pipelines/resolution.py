"""
SlothOps Engine — Auto Resolution
Triggered after a successful rollback to fix the code on the backup branch.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from app import database as db
from app.code_analysis.build_fixer import generate_build_fix
from app.code_analysis.deployment_logs import fetch_deployment_logs
from app.integrations.github_app import get_repo_for_installation
from app.models import AuditAction, AuditEvent, ResolutionRecord, ResolutionStatus
from app.policy import get_effective_policy
from github import GithubException
from app.sse_manager import broadcast
from app.integrations.email_sender import send_resolution_notification_email
from app.code_analysis.stack_detector import detect_stack

logger = logging.getLogger("slothops.resolution")

MAX_RESOLUTION_ATTEMPTS = 3


async def attempt_resolution(
    rollback_id: str,
    workspace_id: str,
    repo_name: str,
    backup_branch: str,
    build_error_log: str,
    failed_sha: str,
    github_app_id: int,
    github_app_private_key: str,
    db_path: str,
    smtp_config: dict | None = None
) -> None:
    """
    Attempt to auto-resolve a build failure on the backup branch.
    Fetches broken files, calls LLM, commits fix to backup branch, and opens PR.
    """
    logger.info("Starting resolution for rollback %s on branch %s", rollback_id, backup_branch)

    policy = await get_effective_policy(workspace_id, repo_name, db_path)
    max_attempts = int(policy.get("max_resolution_attempts", MAX_RESOLUTION_ATTEMPTS))

    # Calculate attempt number
    existing_resolutions = await db.get_resolutions_for_rollback(rollback_id, db_path)
    attempt_number = len(existing_resolutions) + 1

    if attempt_number > max_attempts:
        logger.warning("Max resolution attempts (%d) reached for rollback %s. Abandoning.", max_attempts, rollback_id)
        await db.create_audit_event(AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            repo_name=repo_name,
            action=AuditAction.RESOLUTION_COMPLETED.value,
            target_type="rollback",
            target_id=rollback_id,
            metadata_json={"status": ResolutionStatus.ABANDONED.value},
        ), db_path)
        return

    res_id = str(uuid.uuid4())
    record = ResolutionRecord(
        id=res_id,
        rollback_id=rollback_id,
        workspace_id=workspace_id,
        repo_name=repo_name,
        backup_branch=backup_branch,
        attempt_number=attempt_number,
        build_error_log=build_error_log,
        status=ResolutionStatus.PENDING.value
    )
    await db.create_resolution(record, db_path)
    await broadcast("resolution_event", record.model_dump())

    # Auth GitHub
    integration_record = await db.get_integration(workspace_id, db_path)
    if not integration_record or not integration_record.github_installation_id:
        logger.error("No GitHub App linked for workspace %s.", workspace_id)
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.BUILD_FAILED.value)
        return

    installation_id = int(integration_record.github_installation_id)
    try:
        repo, _ = get_repo_for_installation(github_app_id, github_app_private_key, installation_id, repo_name)
    except Exception as e:
        logger.error("Failed to auth GitHub App for Resolution: %s", e)
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.BUILD_FAILED.value)
        return

    # Fetch broken code context Context
    try:
        commit_obj = repo.get_commit(failed_sha)
        code_context = {}
        for f in commit_obj.files:
            if f.status != "removed" and f.filename.endswith((".ts", ".js", ".tsx", ".jsx", ".py", ".go")):
                try:
                    file_content = repo.get_contents(f.filename, ref=backup_branch)
                    if not isinstance(file_content, list):
                        code_context[f.filename] = file_content.decoded_content.decode("utf-8")
                except GithubException:
                    pass
    except Exception as e:
        logger.warning("Could not fetch changed files for PR commit: %s", e)
        code_context = {}

    if not code_context:
        logger.error("No code context found to resolve issue.")
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.BUILD_FAILED.value)
        return

    logs = fetch_deployment_logs(repo, failed_sha, fallback=build_error_log)
    stack_config = {"language": "unknown", "framework": "unknown"}
    try:
        contents = repo.get_contents(".slothops.yml", ref=backup_branch)
        if not isinstance(contents, list):
            stack_config["slothops_config"] = contents.decoded_content.decode("utf-8", errors="replace")
    except Exception:
        pass

    # Call LLM
    try:
        fix = await generate_build_fix(
            build_logs=logs["logs"],
            code_context=code_context,
            stack_config=stack_config,
            failed_sha=failed_sha,
            attempt_number=attempt_number,
        )
    except Exception as e:
        logger.error("LLM failed to generate resolution: %s", e)
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.BUILD_FAILED.value)
        return

    # Commit fix to backup branch
    try:
        all_changes = fix.files_changed + fix.generated_tests
        for fc in all_changes:
            try:
                existing = repo.get_contents(fc.path, ref=backup_branch)
                if not isinstance(existing, list):
                    repo.update_file(
                        path=fc.path,
                        message=f"resolving build error: {fc.explanation[:72]}",
                        content=fc.fixed_content,
                        sha=existing.sha,
                        branch=backup_branch,
                    )
            except GithubException as exc:
                if exc.status == 404:
                    repo.create_file(
                        path=fc.path,
                        message=f"resolving build error: {fc.explanation[:72]}",
                        content=fc.fixed_content,
                        branch=backup_branch,
                    )
                else:
                    logger.error("Failed to push resolution file %s: %s", fc.path, exc)
                    
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.FIX_PUSHED.value)
        record.status = ResolutionStatus.FIX_PUSHED.value
        await broadcast("resolution_event", record.model_dump())
    except Exception as e:
        logger.error("Failed to push resolution commits: %s", e)
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.BUILD_FAILED.value)
        return

    # Open PR if not exists
    pr_url = None
    pr_number = None
    try:
        # Check if PR from backup to main already exists
        pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{backup_branch}", base="main")
        if pulls.totalCount > 0:
            pr = pulls[0]
            pr.create_issue_comment("🔄 **SlothOps Auto-Resolution**\n\nI have generated a new fix and pushed it to this branch. The CI should re-run automatically.")
            pr_url = pr.html_url
            pr_number = pr.number
        else:
            pr_body = (
                f"## 🦥 SlothOps Auto-Resolution\n\n"
                f"### Build Error Fixed\n"
                f"The previous commit (`{failed_sha[:8]}`) caused a deployment failure. "
                f"SlothOps has automatically analyzed the logs and generated this fix.\n\n"
                f"### Error Log Excerpt\n"
                f"```text\n{build_error_log[:500]}...\n```\n\n"
            )
            for fc in all_changes:
                pr_body += f"\n### `{fc.path}`\n{fc.explanation}\n"
                
            pr = repo.create_pull(
                title=f"fix: Attempt {attempt_number} to resolve build failure from {failed_sha[:8]}",
                body=fix.pr_body or pr_body,
                head=backup_branch,
                base="main",
                draft=True,
            )
            pr_url = pr.html_url
            pr_number = pr.number
            
        await db.update_resolution(
            res_id, 
            db_path, 
            status=ResolutionStatus.PR_OPENED.value,
            resolution_pr_url=pr_url,
            resolution_pr_number=pr_number
        )
        record.status = ResolutionStatus.PR_OPENED.value
        record.resolution_pr_url = pr_url
        record.resolution_pr_number = pr_number
        await broadcast("resolution_event", record.model_dump())
        
        # Email Notification
        if smtp_config and smtp_config.get("QA_EMAIL_RECIPIENT"):
            send_resolution_notification_email({
                "repo_name": repo_name,
                "backup_branch": backup_branch,
                "pr_url": pr_url,
                "attempt_number": attempt_number,
                "build_error_log": build_error_log
            }, smtp_config["QA_EMAIL_RECIPIENT"], smtp_config["SMTP_HOST"], smtp_config["SMTP_PORT"], smtp_config["SMTP_USER"], smtp_config["SMTP_PASSWORD"])

    except Exception as e:
        logger.error("Failed to open resolution PR: %s", e)
        await db.update_resolution(res_id, db_path, status=ResolutionStatus.BUILD_FAILED.value)
