import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app import database as db
from app.models import RepoConfig, RollbackStatus
from app.pipelines.rollback import plan_rollback


@pytest.mark.asyncio
async def test_deployment_failure_plans_pending_approval_rollback(tmp_path):
    db_path = str(tmp_path / "slothops.db")
    await db.init_db(db_path)
    await db.upsert_repo_config(
        RepoConfig(
            workspace_id="ws1",
            repo_name="org/repo",
            config_json={"rollback_mode": "approval_required", "rollback_strategy": "rollback_pr"},
        ),
        db_path,
    )

    record = await plan_rollback(
        workspace_id="ws1",
        repo_name="org/repo",
        failed_sha="abc123def456",
        github_app_id=123,
        github_app_private_key="key",
        db_path=db_path,
        failure_reason="deployment failed",
        environment="production",
        deployment_ref="main",
        deployment_url="https://ci.example/run/1",
    )

    assert record.status == RollbackStatus.PENDING_APPROVAL.value
    assert record.rollback_strategy == "rollback_pr"
    assert record.environment == "production"


@pytest.mark.asyncio
async def test_approve_rollback_updates_approval_metadata(tmp_path):
    db_path = str(tmp_path / "slothops.db")
    await db.init_db(db_path)

    record = await plan_rollback(
        workspace_id="ws1",
        repo_name="org/repo",
        failed_sha="abc123def456",
        github_app_id=123,
        github_app_private_key="key",
        db_path=db_path,
    )
    await db.approve_rollback(record.id, approved_by="user1", reason="safe to revert", db_path=db_path)

    approved = await db.get_rollback(record.id, db_path)
    assert approved.status == RollbackStatus.APPROVED.value
    assert approved.approved_by == "user1"
    assert approved.approval_reason == "safe to revert"
    assert approved.approved_at is not None


@pytest.mark.asyncio
async def test_duplicate_failed_sha_reuses_existing_rollback(tmp_path):
    db_path = str(tmp_path / "slothops.db")
    await db.init_db(db_path)

    first = await plan_rollback("ws1", "org/repo", "abc123def456", 123, "key", db_path)
    second = await plan_rollback("ws1", "org/repo", "abc123def456", 123, "key", db_path)

    assert second.id == first.id
