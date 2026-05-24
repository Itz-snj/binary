"""Webhook router — Sentry and GitHub.

These handlers are the biggest in main.py; they orchestrate the
pipeline, QA, rollback, and resolution flows. Routes are unchanged
so existing webhook configurations keep working.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import database as db
from app.core.config import load_settings
from app.models import AuditAction, AuditEvent
from app.pipelines.pipeline import run_pipeline
from app.integrations.sentry_parser import parse_sentry_webhook
from app.integrations.webhook_security import (
    extract_github_delivery_id,
    verify_github_signature,
    verify_sentry_signature,
)

logger = logging.getLogger("slothops.api.webhooks")

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/sentry/{workspace_id}")
async def receive_sentry_webhook(workspace_id: str, request: Request):
    """Receive a Sentry webhook, parse it, bind to workspace, and kick
    off the pipeline async. Returns 200 immediately so Sentry doesn't retry.
    """
    settings = load_settings()
    raw_body = await request.body()
    integration = await db.get_integration(workspace_id, settings.database_path)
    sentry_secret = integration.sentry_webhook_secret if integration else None
    sentry_signature = (
        request.headers.get("x-sentry-signature")
        or request.headers.get("sentry-hook-signature")
    )
    if not verify_sentry_signature(raw_body, sentry_signature, sentry_secret):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8") or "{}")
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    try:
        issue, call_frames = parse_sentry_webhook(payload)
        issue.workspace_id = workspace_id
        project_slug = (
            payload.get("project_slug")
            or payload.get("data", {}).get("event", {}).get("project")
            or payload.get("data", {}).get("event", {}).get("project_slug")
        )
        repo_config = (
            await db.get_repo_config_by_sentry_project(
                workspace_id, str(project_slug), settings.database_path,
            )
            if project_slug
            else None
        )
        if not repo_config:
            repo_config = await db.get_active_repo_config(
                workspace_id, settings.database_path,
            )
        if not repo_config:
            return JSONResponse(
                {"error": "No repo configured for this Sentry project"},
                status_code=409,
            )
        issue.repo_name = repo_config.repo_name
        issue.raw_payload = json.dumps({
            "frames": [f.model_dump() for f in call_frames],
            "original": payload,
        })
    except Exception as exc:
        logger.error("Failed to parse Sentry payload: %s", exc)
        return JSONResponse({"error": "Parse failed"}, status_code=400)

    logger.info(
        "Webhook received: %s — %s in %s",
        issue.error_type, issue.error_message, issue.file_path,
    )

    asyncio.create_task(run_pipeline(
        issue=issue,
        db_path=settings.database_path,
        github_app_id=settings.github_app_id,
        github_app_private_key=settings.github_app_private_key,
    ))

    return JSONResponse({"status": "accepted", "issue_id": issue.id})


@router.post("/webhook/github")
async def receive_github_webhook(request: Request):
    """Receives GitHub App webhook events: PR open/sync, deployment
    failures, app install/uninstall.
    """
    settings = load_settings()
    raw_body = await request.body()
    if not verify_github_signature(
        raw_body,
        request.headers.get("x-hub-signature-256"),
        settings.github_webhook_secret,
    ):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    action = payload.get("action")
    installation = payload.get("installation", {})
    installation_id = str(installation.get("id", ""))

    github_event = request.headers.get("x-github-event")
    repo_name = payload.get("repository", {}).get("full_name")
    workspace_id = (
        await db.get_workspace_by_installation_id(
            installation_id, settings.database_path,
        )
        if installation_id
        else None
    )
    delivery_id = extract_github_delivery_id(request.headers)
    if delivery_id:
        is_new = await db.record_webhook_delivery(
            delivery_id, github_event or "", workspace_id, repo_name,
            settings.database_path,
        )
        if not is_new:
            return {"status": "duplicate_ignored"}
        if workspace_id:
            await db.create_audit_event(AuditEvent(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                repo_name=repo_name,
                action=AuditAction.WEBHOOK_RECEIVED.value,
                target_type="github_delivery",
                target_id=delivery_id,
                metadata_json={"event": github_event, "action": action},
            ), settings.database_path)

    if github_event == "pull_request" and action in ["opened", "synchronize"]:
        if installation_id and workspace_id:
            from app.integrations.github_automation import handle_human_pr_review
            from app.pipelines.qa_pipeline import run_qa_pipeline

            sender_login = payload.get("sender", {}).get("login", "")

            if sender_login.endswith("[bot]") or "slothops" in sender_login.lower():
                logger.info(
                    "Bot commit detected from %s, running QA only (skipping review)",
                    sender_login,
                )
                asyncio.create_task(run_qa_pipeline(
                    payload=payload,
                    workspace_id=workspace_id,
                    github_app_id=settings.github_app_id,
                    github_app_private_key=settings.github_app_private_key,
                    db_path=settings.database_path,
                    repo_name=repo_name,
                ))
                return {"status": "qa_only_queued"}

            logger.info(
                "Received Human PR event %s for workspace %s, queuing review + delayed QA...",
                action, workspace_id,
            )

            async def _delayed_qa():
                # Stagger LLM calls to prevent quota spikes.
                await asyncio.sleep(5)
                await run_qa_pipeline(
                    payload=payload,
                    workspace_id=workspace_id,
                    github_app_id=settings.github_app_id,
                    github_app_private_key=settings.github_app_private_key,
                    db_path=settings.database_path,
                    repo_name=repo_name,
                )

            asyncio.create_task(handle_human_pr_review(
                payload=payload,
                workspace_id=workspace_id,
                github_app_id=settings.github_app_id,
                github_app_private_key=settings.github_app_private_key,
                db_path=settings.database_path,
            ))
            asyncio.create_task(_delayed_qa())
            return {"status": "review_and_qa_queued"}

    if github_event == "deployment_status":
        deployment_status = payload.get("deployment_status", {})
        state = deployment_status.get("state")
        if state in ["error", "failure"] and installation_id and workspace_id:
            sha = payload.get("deployment", {}).get("sha")
            ref = payload.get("deployment", {}).get("ref", "")
            if sha and repo_name:
                if str(ref).startswith("slothops/backup-"):
                    rollback_record = await db.get_rollback_by_backup_branch(
                        str(ref), settings.database_path,
                    )
                    if rollback_record:
                        from app.pipelines.resolution import attempt_resolution
                        logger.info(
                            "Received re-cycle deployment failure for resolution PR %s", ref,
                        )

                        smtp_config = {
                            "SMTP_HOST": os.getenv("SMTP_HOST", ""),
                            "SMTP_PORT": int(os.getenv("SMTP_PORT", 587)),
                            "SMTP_USER": os.getenv("SMTP_USER", ""),
                            "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
                            "QA_EMAIL_RECIPIENT": os.getenv("QA_EMAIL_RECIPIENT", ""),
                        }

                        asyncio.create_task(attempt_resolution(
                            rollback_id=rollback_record.id,
                            workspace_id=workspace_id,
                            repo_name=repo_name,
                            backup_branch=str(ref),
                            build_error_log=f"Deployment status reported {state}",
                            failed_sha=sha,
                            github_app_id=settings.github_app_id,
                            github_app_private_key=settings.github_app_private_key,
                            db_path=settings.database_path,
                            smtp_config=smtp_config,
                        ))
                        return {"status": "resolution_queued"}

                from app.pipelines.rollback import plan_rollback
                logger.info(
                    "Received deployment failure for %s, planning rollback...", sha[:8],
                )
                asyncio.create_task(plan_rollback(
                    workspace_id=workspace_id,
                    repo_name=repo_name,
                    failed_sha=sha,
                    github_app_id=settings.github_app_id,
                    github_app_private_key=settings.github_app_private_key,
                    db_path=settings.database_path,
                    failure_reason=f"Deployment status reported {state}",
                    environment=deployment_status.get("environment"),
                    deployment_ref=ref,
                    deployment_url=(
                        deployment_status.get("target_url")
                        or deployment_status.get("log_url")
                    ),
                ))
                return {"status": "rollback_planned"}

    if payload.get("installation") and action == "created" and installation_id:
        # Auto-link: find a workspace without a GitHub integration yet
        # and bind this installation to it. The frontend /api/github/link
        # endpoint is the primary pairing mechanism; this is a backup.
        workspaces = await db.list_workspaces(settings.database_path)
        for ws in workspaces:
            existing_integration = await db.get_integration(
                ws.id, settings.database_path,
            )
            if not existing_integration or not existing_integration.github_installation_id:
                from app.models import Integration
                integration = Integration(
                    workspace_id=ws.id,
                    github_installation_id=installation_id,
                )
                await db.upsert_integration(integration, settings.database_path)
                logger.info(
                    "Auto-linked GitHub Installation %s to Workspace %s",
                    installation_id, ws.id,
                )
                return {"status": "linked", "workspace": ws.id}

        logger.info(
            "GitHub Installation %s received but no unlinked workspace available. "
            "User should link via dashboard.",
            installation_id,
        )

    elif payload.get("installation") and action == "deleted" and installation_id:
        workspaces = await db.list_workspaces(settings.database_path)
        for ws in workspaces:
            integration = await db.get_integration(ws.id, settings.database_path)
            if integration and integration.github_installation_id == installation_id:
                from app.models import Integration
                cleared = Integration(workspace_id=ws.id, github_installation_id="")
                await db.upsert_integration(cleared, settings.database_path)
                logger.info(
                    "Unlinked GitHub Installation %s from Workspace %s (app uninstalled)",
                    installation_id, ws.id,
                )
                break

    return {"status": "ok"}
