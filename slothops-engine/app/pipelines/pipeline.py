"""
SlothOps Engine — Pipeline Orchestrator
Runs the full remediation pipeline for a single issue:
  parse → redact → fingerprint → classify → fetch → fix → PR

Each stage updates the DB status and broadcasts an SSE event.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import database as db
from classifier import classify
from code_fetcher import fetch_code_context, fetch_deep_code_context
import asyncio
import uuid
from fingerprint import check_dedup, compute_fingerprint
from github_automation import create_fix_pr
from github_app import get_repo_for_installation
from llm_fixer import generate_fix, generate_infra_recommendation
from models import AuditAction, AuditEvent, CallFrame, DedupeAction, IssueRecord, IssueStatus
from redactor import redact
from sse_manager import broadcast

logger = logging.getLogger("slothops.pipeline")

# Extension → language mapping for code_fetcher
EXTENSION_TO_LANGUAGE = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
}


def _infer_language(file_path: str | None) -> str:
    """Infer language from file extension."""
    if not file_path:
        return "javascript"
    ext = os.path.splitext(file_path)[1]
    return EXTENSION_TO_LANGUAGE.get(ext, "javascript")


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
    github_app_id: str | None = None,
    github_app_private_key: str | None = None,
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
        await db.create_audit_event(AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=issue.workspace_id,
            repo_name=issue.repo_name,
            action=AuditAction.ISSUE_RECEIVED.value,
            target_type="issue",
            target_id=issue.id,
            metadata_json={"error_type": issue.error_type},
        ), db_path)
        issue.stack_trace = redact(issue.stack_trace or "")
        issue.error_message = redact(issue.error_message or "")
        logger.info("[%s] Redaction complete", issue.id[:8])

        # ── 2. Fingerprint + Dedup ───────────────────────────────────
        fp = compute_fingerprint(issue.error_type, issue.file_path, issue.function_name, issue.error_message)
        issue.fingerprint = fp

        # Initialize for use in deep scan
        call_chain: list[CallFrame] = []

        existing = await db.get_issue_by_fingerprint(fp, issue.workspace_id, db_path)

        if existing:
            action = check_dedup(existing.status, existing.updated_at)
            if action == DedupeAction.SKIP:
                await db.increment_occurrence(existing.id, issue.workspace_id, db_path)
                await broadcast("status_update", {
                    "id": existing.id,
                    "status": existing.status,
                    "message": "Duplicate — skipped",
                })
                logger.info("[%s] Duplicate fingerprint, skipping", issue.id[:8])
                await db.create_audit_event(AuditEvent(
                    id=str(uuid.uuid4()),
                    workspace_id=issue.workspace_id,
                    repo_name=issue.repo_name,
                    action=AuditAction.ISSUE_DUPLICATE_SKIPPED.value,
                    target_type="issue",
                    target_id=existing.id,
                    metadata_json={"fingerprint": fp},
                ), db_path)
                return
            elif action == DedupeAction.RETRIGGER:
                # Mark old fix as ineffective
                await db.update_issue_status(
                    existing.id, db_path, status=IssueStatus.FIX_INEFFECTIVE.value
                )
                issue.previous_fix_id = existing.id
                logger.info("[%s] Re-triggering: previous fix ineffective — deep scan enabled", issue.id[:8])

                # Deep call chain: parse frames from stored payload
                try:
                    stored = json.loads(existing.raw_payload or "{}")
                    frame_list = stored.get("frames", [])
                    call_chain = [CallFrame(**f) for f in frame_list]
                except Exception:
                    call_chain = []

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
            if classification == "infra":
                logger.info("[%s] Fetching Infra Recommendation from Gemini", issue.id[:8])
                await _update(issue, db_path, IssueStatus.FIXING.value)
                try:
                    recommendation = await generate_infra_recommendation(issue)
                except Exception as e:
                    recommendation = f"Failed to generate recommendation: {e}"
                    
                await _update(
                    issue, db_path,
                    IssueStatus.RECOMMENDATION_ONLY.value,
                    root_cause="Infrastructure failure detected",
                    recommendation=recommendation
                )
                return
                
            await _update(issue, db_path, IssueStatus.IGNORED.value)
            logger.info("[%s] Not a code error — ignored", issue.id[:8])
            return

        # ── 4. Build GitHub Client & Fetch context ───────────────────
        await _update(issue, db_path, IssueStatus.FIXING.value)

        try:
            if not github_app_id or not github_app_private_key:
                logger.error("[%s] GitHub App not configured (GITHUB_APP_ID or GITHUB_APP_PRIVATE_KEY missing from .env)", issue.id[:8])
                await _update(issue, db_path, "fixing_failed", root_cause="GitHub App not configured. Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY in .env")
                return

            # Load private key — support both inline and file path
            private_key = github_app_private_key
            if private_key and os.path.isfile(private_key):
                with open(private_key, "r") as f:
                    private_key = f.read()
            
            # Get the installation_id from the workspace's integrations table
            integration = await db.get_integration(issue.workspace_id, db_path)
            
            if not integration or not integration.github_installation_id:
                logger.error("[%s] No GitHub App installation linked for workspace %s. "
                             "User must install the GitHub App on their repository first.",
                             issue.id[:8], issue.workspace_id)
                await _update(issue, db_path, "fixing_failed", 
                              root_cause="GitHub App not installed. Go to Settings in your SlothOps dashboard and install the GitHub App on your repository.")
                return

            if not issue.repo_name:
                active_config = await db.get_active_repo_config(issue.workspace_id, db_path)
                issue.repo_name = active_config.repo_name if active_config else None
            if not issue.repo_name:
                raise Exception("No repo configured for this issue")

            repo, installation_auth = get_repo_for_installation(
                github_app_id, private_key, integration.github_installation_id, issue.repo_name
            )
            logger.info("[%s] ✅ Authenticated via GitHub App (Installation %s) → Repo: %s", 
                        issue.id[:8], integration.github_installation_id, repo.full_name)

        except Exception as exc:
            logger.error("[%s] GitHub client init failed: %s", issue.id[:8], exc)
            await _update(issue, db_path, "fixing_failed", root_cause=str(exc))
            return

        # Check if this is a recurrence (deep scan mode)
        is_recurrence = issue.previous_fix_id is not None
        language = _infer_language(issue.file_path)

        if is_recurrence:
            code_context = fetch_deep_code_context(
                file_path=issue.file_path,
                call_chain=call_chain,
                repo=repo,
                language=language,
            )
            logger.info("[%s] Deep scan: fetched %d file(s) from call chain", issue.id[:8], len(code_context))
        else:
            code_context = fetch_code_context(
                file_path=issue.file_path,
                repo=repo,
                language=language,
            )
            logger.info("[%s] First pass: fetched %d file(s)", issue.id[:8], len(code_context))

        if not code_context:
            logger.warning("[%s] No code context found — cannot generate fix", issue.id[:8])
            await _update(issue, db_path, "fixing_failed",
                          root_cause="Could not fetch source files from GitHub")
            return

        # ── 5. LLM fix generation ────────────────────────────────────
        previous_pr_url: Optional[str] = None
        if issue.previous_fix_id:
            prev = await db.get_issue(issue.previous_fix_id, issue.workspace_id, db_path)
            previous_pr_url = prev.fix_pr_url if prev else None

        try:
            fix = await generate_fix(
                issue=issue,
                code_context=code_context,
                previous_pr_url=previous_pr_url,
                call_chain=call_chain if is_recurrence else None,
                repo=repo,
            )
        except RuntimeError as exc:
            logger.error("[%s] LLM fix failed: %s", issue.id[:8], exc)
            await _update(issue, db_path, "fixing_failed", root_cause=str(exc))
            return

        issue.confidence = fix.confidence
        issue.root_cause = fix.root_cause
        await db.create_audit_event(AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=issue.workspace_id,
            repo_name=issue.repo_name,
            action=AuditAction.FIX_GENERATED.value,
            target_type="issue",
            target_id=issue.id,
            metadata_json={"confidence": fix.confidence},
        ), db_path)
        logger.info("[%s] Fix generated (confidence: %s)", issue.id[:8], fix.confidence)

        # ── 5.5. Local Test Validation (Smart Sandbox Gating) ────────
        def _should_run_sandbox(fix_response) -> bool:
            """Only spin up an expensive sandbox for multi-file, confident fixes."""
            if not fix_response.generated_tests:
                return False
            if fix_response.confidence == "low":
                return False
            if len(fix_response.files_changed) < 2:
                return False
            return True

        if _should_run_sandbox(fix):
            logger.info("[%s] 🧪 Sandbox triggered (multi-file %s-confidence fix with %d test(s))",
                        issue.id[:8], fix.confidence, len(fix.generated_tests))
            await _update(issue, db_path, "validating_fix")
            
            from test_runner import validate_fix
            from llm_fixer import retry_fix_with_test_failure
            
            test_passed, test_output = await asyncio.to_thread(
                validate_fix, fix, repo, installation_auth.token
            )
            
            if not test_passed:
                logger.warning("[%s] Tests failed. Attempting to re-fix...", issue.id[:8])
                await _update(issue, db_path, "tests_failed")
                try:
                    await _update(issue, db_path, "refixing")
                    fix = await retry_fix_with_test_failure(
                        issue=issue,
                        code_context=code_context,
                        previous_fix=fix,
                        test_output=test_output,
                        previous_pr_url=previous_pr_url,
                        call_chain=call_chain if is_recurrence else None,
                    )
                    
                    # Update issue with new fix details
                    issue.confidence = fix.confidence
                    issue.root_cause = fix.root_cause
                    
                    logger.info("[%s] Validating re-fix...", issue.id[:8])
                    await _update(issue, db_path, "validating_fix")
                    test_passed, test_output = await asyncio.to_thread(
                        validate_fix, fix, repo, installation_auth.token
                    )
                    
                    if not test_passed:
                        logger.warning("[%s] Re-fix failed tests. Proceeding with warning.", issue.id[:8])
                        await _update(issue, db_path, "tests_failed")
                        fix.pr_body += "\n\n> ⚠️ **Warning:** Generated tests failed during validation. Manual review required.\n\n<details><summary>Test Output</summary>\n\n```text\n" + test_output + "\n```\n</details>"
                except Exception as exc:
                    logger.error("[%s] Re-fix generation failed: %s", issue.id[:8], exc)
                    await _update(issue, db_path, "tests_failed")
                    fix.pr_body += "\n\n> ⚠️ **Warning:** Generated tests failed and automatic re-fix threw an error."
            else:
                logger.info("[%s] ✅ Generated tests passed!", issue.id[:8])
                await _update(issue, db_path, "tests_passed")
        elif fix.generated_tests:
            logger.info("[%s] ⏭️  Skipping sandbox (single-file or low-confidence fix)", issue.id[:8])

        # ── 6. Confidence gating ─────────────────────────────────────
        if fix.confidence == "low":
            await _update(
                issue, db_path,
                IssueStatus.RECOMMENDATION_ONLY.value,
                confidence=fix.confidence,
                root_cause=fix.root_cause,
                recommendation=fix.pr_body,
            )
            await db.create_audit_event(AuditEvent(
                id=str(uuid.uuid4()),
                workspace_id=issue.workspace_id,
                repo_name=issue.repo_name,
                action=AuditAction.RECOMMENDATION_ONLY.value,
                target_type="issue",
                target_id=issue.id,
                metadata_json={"confidence": fix.confidence},
            ), db_path)
            logger.info("[%s] Low confidence — stored recommendation only", issue.id[:8])
            return

        # ── 7. Create GitHub PR ──────────────────────────────────────
        try:
            pr_info = create_fix_pr(
                issue=issue,
                fix=fix,
                repo=repo,
            )
        except RuntimeError as exc:
            logger.error("[%s] PR creation failed: %s", issue.id[:8], exc)
            await _update(issue, db_path, "pr_creation_failed", root_cause=str(exc))
            return

        pr_url = pr_info["url"]
        await _update(
            issue, db_path,
            IssueStatus.PR_CREATED.value,
            confidence=fix.confidence,
            root_cause=fix.root_cause,
            fix_pr_url=pr_url,
            fix_pr_branch=pr_info["branch"],
        )
        await db.create_audit_event(AuditEvent(
            id=str(uuid.uuid4()),
            workspace_id=issue.workspace_id,
            repo_name=issue.repo_name,
            action=AuditAction.PR_CREATED.value,
            target_type="issue",
            target_id=issue.id,
            metadata_json=pr_info,
        ), db_path)
        logger.info("[%s] ✅ Draft PR created: %s", issue.id[:8], pr_url)

        # ── 8. Style & Code Review ─────────────────────────────────────────
        try:
            from style_reviewer import review_against_preferences
            from github_automation import post_style_review_comments
            dev_config = await db.get_developer_config(issue.workspace_id, db_path)
            if dev_config:
                logger.info("[%s] 🎨 Running style review against developer.json...", issue.id[:8])
                changed_files_list = [{"path": fc.path, "content": fc.fixed_content} for fc in fix.files_changed]
                style_comments = await review_against_preferences(changed_files_list, dev_config)
                if style_comments:
                    post_style_review_comments(pr_url, style_comments, repo)
                    logger.info("[%s] 🎨 Posted %d style suggestion(s) on PR", issue.id[:8], len(style_comments))
                else:
                    logger.info("[%s] 🎨 No style violations found", issue.id[:8])
            else:
                logger.info("[%s] No developer.json configured — skipping style review", issue.id[:8])
                    
            # ── 9. Architecture / Logic Review ─────────────────────────
            from code_reviewer import review_pr_code
            from github_automation import post_general_pr_comment
            logger.info("[%s] 🧠 Running architecture code review...", issue.id[:8])
            
            # Try to grab AI_CONTEXT.md
            try:
                ai_context_file = repo.get_contents("AI_CONTEXT.md")
                context_str = ai_context_file.decoded_content.decode("utf-8")
            except Exception:
                context_str = ""
                
            code_review_md = await review_pr_code(
                changed_files=[{"path": fc.path, "content": fc.fixed_content} for fc in fix.files_changed],
                codebase_context=context_str,
            )
            if code_review_md:
                post_general_pr_comment(pr_url, code_review_md, repo)
                logger.info("[%s] 🧠 Posted code review comment on PR", issue.id[:8])
                
        except Exception as exc:
            logger.warning("[%s] Style/Code review failed (non-fatal): %s", issue.id[:8], exc)

    except Exception as exc:
        logger.exception("[%s] Unhandled pipeline error: %s", issue.id[:8], exc)
        try:
            await _update(issue, db_path, "fixing_failed", root_cause=f"Unhandled: {exc}")
        except Exception:
            pass
