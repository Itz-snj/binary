import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qa_triage import triage_pr


def test_docs_assets_only():
    result = triage_pr(["README.md", "static/style.css"])
    assert result.risk_level == "low"
    assert result.required_agents == []
    assert result.advisory_agents == ["static_analysis"]


def test_dependency_change():
    result = triage_pr(["package.json", "src/app.ts"])
    assert "dependency_change" in result.categories
    assert result.required_agents == ["static_analysis", "regression", "vapt"]


def test_auth_api_change_high_risk():
    result = triage_pr(["src/routes/auth.ts"])
    assert result.risk_level == "high"
    assert "security_sensitive" in result.categories


def test_test_only():
    result = triage_pr(["tests/users.test.ts"])
    assert result.required_agents == ["regression"]
    assert result.advisory_agents == []
