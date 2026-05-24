import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from pathlib import Path

import pytest

from app import database as db
from app.models import RepoConfig
from app.integrations.sentry_parser import parse_sentry_webhook


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_sentry_project_maps_to_repo_and_sets_issue_repo_name(tmp_path):
    db_path = str(tmp_path / "slothops.db")
    await db.init_db(db_path)
    await db.upsert_repo_config(
        RepoConfig(
            workspace_id="ws1",
            repo_name="org/api",
            config_json={},
            sentry_project_slug="api",
        ),
        db_path,
    )
    payload = json.loads((FIXTURES_DIR / "sentry_webhook.json").read_text())
    payload["project_slug"] = "api"

    issue, _ = parse_sentry_webhook(payload)
    repo_config = await db.get_repo_config_by_sentry_project("ws1", payload["project_slug"], db_path)
    issue.workspace_id = "ws1"
    issue.repo_name = repo_config.repo_name

    assert issue.repo_name == "org/api"
