import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.policy import merge_policy


def test_default_policy():
    policy = merge_policy(None)
    assert policy["rollback_mode"] == "approval_required"
    assert policy["rollback_strategy"] == "rollback_pr"
    assert "static_analysis" in policy["required_agents"]


def test_repo_override_and_nested_qa_policy():
    policy = merge_policy({
        "rollback_mode": "suggest_only",
        "qa_policy": {
            "warnings_block_merge": True,
            "required_agents": ["regression"],
        },
    })
    assert policy["rollback_mode"] == "suggest_only"
    assert policy["warnings_block_merge"] is True
    assert policy["required_agents"] == ["regression"]
