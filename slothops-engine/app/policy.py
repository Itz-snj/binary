"""Repo policy resolution for SlothOps workflows."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

from app import database as db


DEFAULT_POLICY: dict[str, Any] = {
    "rollback_mode": os.getenv("ROLLBACK_DEFAULT_MODE", "approval_required"),
    "rollback_strategy": os.getenv("ROLLBACK_DEFAULT_STRATEGY", "rollback_pr"),
    "required_agents": ["static_analysis", "regression", "vapt"],
    "advisory_agents": ["functionality"],
    "warnings_block_merge": False,
    "allowed_environments": ["production"],
    "max_resolution_attempts": 3,
    "stress_enabled": False,
}


def merge_policy(overrides: dict | None) -> dict:
    policy = deepcopy(DEFAULT_POLICY)
    if overrides:
        qa_policy = overrides.get("qa_policy", {}) if isinstance(overrides.get("qa_policy"), dict) else {}
        merged = {**overrides, **qa_policy}
        for key, value in merged.items():
            if key in policy and value is not None:
                policy[key] = value
    return policy


async def get_effective_policy(workspace_id: str, repo_name: str | None, db_path: str) -> dict:
    config = None
    if repo_name:
        config = await db.get_repo_config(workspace_id, repo_name, db_path)
    if not config:
        config = await db.get_active_repo_config(workspace_id, db_path)
    return merge_policy(config.config_json if config else None)
