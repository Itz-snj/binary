"""QA router.

Owns QA report listing, retrieval, operator bypass, and AI-assisted
resolution kickoff. Paths match the legacy main.py routes so the
dashboard keeps working during the migration.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import database as db
from app.core.config import load_settings
from app.core.security import get_current_workspace
from app.sse_manager import broadcast

logger = logging.getLogger("slothops.api.qa")

router = APIRouter(tags=["qa"])


class QABypassRequest(BaseModel):
    reason: str


@router.get("/api/qa-reports")
async def list_qa_reports(workspace_id: str = Depends(get_current_workspace)):
    reports = await db.get_qa_reports(workspace_id, load_settings().database_path)
    return [r.model_dump() for r in reports]


@router.get("/api/qa-reports/{report_id}")
async def get_qa_report(
    report_id: str,
    workspace_id: str = Depends(get_current_workspace),
):
    settings = load_settings()
    report = await db.get_qa_report(report_id, settings.database_path)
    if not report or report.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Not found")
    return report.model_dump()


@router.post("/api/qa-bypass/{report_id}")
async def bypass_qa(
    report_id: str,
    req: QABypassRequest,
    workspace_id: str = Depends(get_current_workspace),
):
    from app.models import QAStatus

    settings = load_settings()
    report = await db.get_qa_report(report_id, settings.database_path)
    if not report or report.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Not found")

    logger.info(
        "QA bypassed for PR #%s by user in workspace %s. Reason: %s",
        report.pr_number, workspace_id, req.reason,
    )
    await db.update_qa_report(
        report_id, settings.database_path,
        overall_status=QAStatus.BYPASSED.value,
        summary=f"Bypassed by operator. Reason: {req.reason}",
    )
    asyncio.create_task(broadcast("qa_update", {"id": report_id, "status": QAStatus.BYPASSED.value}))

    # Set GitHub commit status to success so the merge button unblocks
    try:
        integration = await db.get_integration(workspace_id, settings.database_path)
        if integration and integration.github_installation_id:
            from app.integrations.github_app import get_repo_for_installation
            from app.pipelines.qa_pipeline import _set_commit_status
            repo, _ = get_repo_for_installation(
                settings.github_app_id,
                settings.github_app_private_key,
                integration.github_installation_id,
                report.repo_name,
            )
            _set_commit_status(
                repo, report.commit_sha, "success",
                f"QA bypassed: {req.reason[:100]}", report.pr_url,
            )
            logger.info(
                "Commit status set to success after bypass for SHA %s",
                report.commit_sha[:8],
            )
    except Exception as e:
        logger.error("Failed to set commit status on bypass: %s", e)

    return {"status": "bypassed"}


@router.post("/api/qa-resolve/{report_id}")
async def resolve_qa(
    report_id: str,
    workspace_id: str = Depends(get_current_workspace),
):
    """AI-driven QA resolution: read failed agents' logs, ask LLM for
    fixes, commit to the PR branch. The push triggers a synchronize
    event which re-runs review + QA automatically.
    """
    settings = load_settings()
    report = await db.get_qa_report(report_id, settings.database_path)
    if not report or report.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Not found")

    if report.overall_status not in ("failed", "warning"):
        raise HTTPException(status_code=400, detail="QA is not in a failed/warning state")

    await db.update_qa_report(
        report_id, settings.database_path,
        overall_status="resolving",
        summary="SlothOps is generating fixes for the QA failures...",
    )
    asyncio.create_task(broadcast("qa_update", {"id": report_id, "status": "resolving"}))

    from app.pipelines.qa_resolution import request_qa_resolution
    asyncio.create_task(request_qa_resolution(
        report_id=report_id,
        workspace_id=workspace_id,
        db_path=settings.database_path,
        github_app_id=settings.github_app_id,
        private_key=settings.github_app_private_key,
    ))
    return {
        "status": "resolving",
        "message": "QA resolution started. Fixes will be committed to the PR branch.",
    }
