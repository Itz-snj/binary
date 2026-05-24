"""Rollbacks router.

Owns rollback queue listing, retrieval, and operator approval.
Paths match the legacy main.py routes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import database as db
from app.core.config import load_settings
from app.core.security import get_current_workspace
from app.models import AuditAction, AuditEvent, RollbackStatus

logger = logging.getLogger("slothops.api.rollbacks")

router = APIRouter(tags=["rollbacks"])


class RollbackApprovalRequest(BaseModel):
    reason: str


async def _hydrate(rollback) -> dict:
    settings = load_settings()
    out = rollback.model_dump()
    resolutions = await db.get_resolutions_for_rollback(rollback.id, settings.database_path)
    out["resolutions"] = [r.model_dump() for r in resolutions]
    return out


@router.get("/api/rollbacks")
async def list_rollbacks(workspace_id: str = Depends(get_current_workspace)):
    settings = load_settings()
    rollbacks = await db.get_rollbacks(workspace_id, settings.database_path)
    return [await _hydrate(r) for r in rollbacks]


@router.get("/api/rollbacks/{rollback_id}")
async def get_rollback_record(
    rollback_id: str,
    workspace_id: str = Depends(get_current_workspace),
):
    settings = load_settings()
    rollback = await db.get_rollback(rollback_id, settings.database_path)
    if not rollback or rollback.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Not found")
    return await _hydrate(rollback)


@router.post("/api/rollbacks/{rollback_id}/approve")
async def approve_rollback_endpoint(
    rollback_id: str,
    req: RollbackApprovalRequest,
    workspace_id: str = Depends(get_current_workspace),
):
    settings = load_settings()
    rollback = await db.get_rollback(rollback_id, settings.database_path)
    if not rollback or rollback.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Not found")
    if rollback.status not in (RollbackStatus.PENDING_APPROVAL.value, RollbackStatus.APPROVED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Rollback cannot be approved from status {rollback.status}",
        )
    await db.approve_rollback(
        rollback_id, approved_by=workspace_id, reason=req.reason,
        db_path=settings.database_path,
    )
    await db.create_audit_event(AuditEvent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        repo_name=rollback.repo_name,
        actor=workspace_id,
        action=AuditAction.ROLLBACK_APPROVED.value,
        target_type="rollback",
        target_id=rollback_id,
        metadata_json={"reason": req.reason},
    ), settings.database_path)
    from app.pipelines.rollback import execute_rollback
    asyncio.create_task(execute_rollback(
        rollback_id=rollback_id,
        workspace_id=workspace_id,
        github_app_id=settings.github_app_id,
        github_app_private_key=settings.github_app_private_key,
        db_path=settings.database_path,
    ))
    return {"status": "approved", "rollback_id": rollback_id}
