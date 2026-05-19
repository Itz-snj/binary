import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import database as db
from models import AuditEvent, RepoConfig


@pytest.mark.asyncio
async def test_repo_config_and_delivery_idempotency(tmp_path):
    db_path = str(tmp_path / "slothops.db")
    await db.init_db(db_path)

    cfg = RepoConfig(
        workspace_id="ws1",
        repo_name="org/repo",
        config_json={"rollback_mode": "suggest_only"},
        sentry_project_slug="api",
    )
    await db.upsert_repo_config(cfg, db_path)
    fetched = await db.get_repo_config("ws1", "org/repo", db_path)
    assert fetched.config_json["rollback_mode"] == "suggest_only"

    by_sentry = await db.get_repo_config_by_sentry_project("ws1", "api", db_path)
    assert by_sentry.repo_name == "org/repo"

    assert await db.record_webhook_delivery("d1", "pull_request", "ws1", "org/repo", db_path)
    assert not await db.record_webhook_delivery("d1", "pull_request", "ws1", "org/repo", db_path)

    await db.create_audit_event(AuditEvent(
        id="audit1",
        workspace_id="ws1",
        repo_name="org/repo",
        action="webhook_received",
    ), db_path)
