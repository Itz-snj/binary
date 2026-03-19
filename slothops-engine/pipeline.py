"""
SlothOps Engine — Pipeline Orchestrator
Runs the full remediation pipeline for a single issue:
  parse → redact → fingerprint → classify → fetch → fix → PR

Each stage updates the DB status and broadcasts an SSE event.
"""

from __future__ import annotations

import logging
from typing import Optional

import database as db
from classifier import classify
from code_fetcher import fetch_code_context
from fingerprint import check_dedup, compute_fingerprint
from github_automation import create_fix_pr
from llm_fixer import generate_fix
from models import DedupeAction, IssueRecord, IssueStatus
from redactor import redact
from sse_manager import broadcast

logger = logging.getLogger("slothops.pipeline")


async def _update(
    issue: IssueRecord,
    db_path: str,
    status: str,
    event: str = "status_update",
    **extra_fields,
) -> None:
    """Helper: update DB status + broadcast SSE event."""
    await db.update_issue_status(issue.id, db_path, status=status, **extra_fields)
    await broadcast(event, {"id": issue.id, "status": status, **extra_fields})


async def run_pipeline(
    issue: IssueRecord,
    db_path: str,
    gemini_api_key: str,
    github_token: str,
    github_repo: str,
) -> None:
    """
    Execute the full bug remediation pipeline for one issue.

    This function is meant to be spawned as an ``asyncio.create_task()``
    from the webhook handler so the HTTP response returns immediately.
    """
    logger.info("Pipeline started for issue %s (%s)", issue.id[:8], issue.error_type)

    try:
        # ── 1. Redact ────────────────────────────────────────────────
        await _update(issue, db_path, IssueStatus.TRIAGING.value)
        issue.stack_trace = redact(issue.stack_trace or "")
        issue.error_message = redact(issue.error_message or "")
        logger.info("[%s] Redaction complete", issue.id[:8])

        # ── 2. Fingerprint + Dedup ───────────────────────────────────
        fp = compute_fingerprint(issue.error_type, issue.file_path, issue.function_name)
        issue.fingerprint = fp

        existing = await db.get_issue_by_fingerprint(fp, db_path)

        if existing:
            action = check_dedup(existing.status, existing.updated_at)
            if action == DedupeAction.SKIP:
                await db.increment_occurrence(existing.id, db_path)
                await broadcast("status_update", {
                    "id": existing.id,
                    "status": existing.status,
                    "message": "Duplicate — skipped",
                })
                logger.info("[%s] Duplicate fingerprint, skipping", issue.id[:8])
                return
            elif action == DedupeAction.RETRIGGER:
                # Mark old fix as ineffective
                await db.update_issue_status(
                    existing.id, db_path, status=IssueStatus.FIX_INEFFECTIVE.value
                )
                issue.previous_fix_id = existing.id
                logger.info("[%s] Re-triggering: previous fix ineffective", issue.id[:8])

        # Persist the new issue
        issue.fingerprint = fp
        await db.create_issue(issue, db_path)

        # ── 3. Classify ──────────────────────────────────────────────
        classification = classify(
            error_type=issue.error_type,
            error_message=issue.error_message,
            stack_trace=issue.stack_trace,
            file_path=issue.file_path,
        )
        issue.classification = classification
        await _update(issue, db_path, IssueStatus.CLASSIFIED.value, classification=classification)
        logger.info("[%s] Classified as: %s", issue.id[:8], classification)

        if classification != "code":
            await _update(issue, db_path, IssueStatus.IGNORED.value)
            logger.info("[%s] Not a code error — ignored", issue.id[:8])
            return

        # ── 4. Fetch code context from GitHub ────────────────────────
        await _update(issue, db_path, IssueStatus.FIXING.value)

        code_context = fetch_code_context(
            file_path=issue.file_path,
            github_token=github_token,
            github_repo=github_repo,
        )
        logger.info("[%s] Fetched %d file(s) from GitHub", issue.id[:8], len(code_context))

        if not code_context:
            logger.warning("[%s] No code context found — cannot generate fix", issue.id[:8])
            await _update(issue, db_path, "fixing_failed",
                          root_cause="Could not fetch source files from GitHub")
            return

        # ── 5. LLM fix generation ────────────────────────────────────
        previous_pr_url: Optional[str] = None
        if issue.previous_fix_id:
            prev = await db.get_issue(issue.previous_fix_id, db_path)
            previous_pr_url = prev.fix_pr_url if prev else None

        try:
            fix = generate_fix(
                issue=issue,
                code_context=code_context,
                gemini_api_key=gemini_api_key,
                previous_pr_url=issue.previous_fix_id,
            )
        except RuntimeError as exc:
            logger.error("[%s] LLM fix failed: %s", issue.id[:8], exc)
            await _update(issue, db_path, "fixing_failed", root_cause=str(exc))
            return

        issue.confidence = fix.confidence
        issue.root_cause = fix.root_cause
        logger.info("[%s] Fix generated (confidence: %s)", issue.id[:8], fix.confidence)

        # ── 6. Confidence gating ─────────────────────────────────────
        if fix.confidence == "low":
            await _update(
                issue, db_path,
                IssueStatus.RECOMMENDATION_ONLY.value,
                confidence=fix.confidence,
                root_cause=fix.root_cause,
                recommendation=fix.pr_body,
            )
            logger.info("[%s] Low confidence — stored recommendation only", issue.id[:8])
            return

        # ── 7. Create GitHub PR ──────────────────────────────────────
        try:
            pr_url = create_fix_pr(
                issue=issue,
                fix=fix,
                github_token=github_token,
                github_repo=github_repo,
            )
        except RuntimeError as exc:
            logger.error("[%s] PR creation failed: %s", issue.id[:8], exc)
            await _update(issue, db_path, "pr_creation_failed", root_cause=str(exc))
            return

        await _update(
            issue, db_path,
            IssueStatus.PR_CREATED.value,
            confidence=fix.confidence,
            root_cause=fix.root_cause,
            fix_pr_url=pr_url,
            fix_pr_branch=f"slothops/fix-{issue.id[:8]}",
        )
        logger.info("[%s] ✅ Draft PR created: %s", issue.id[:8], pr_url)

    except Exception as exc:
        logger.exception("[%s] Unhandled pipeline error: %s", issue.id[:8], exc)
        try:
            await _update(issue, db_path, "fixing_failed", root_cause=f"Unhandled: {exc}")
        except Exception:
            pass
