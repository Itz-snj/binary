"""Deterministic PR triage for QA agent selection."""

from __future__ import annotations

from models import QATriageResult


DOC_EXTS = {".md", ".mdx", ".txt", ".rst"}
ASSET_EXTS = {".css", ".scss", ".sass", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
DEPENDENCY_FILES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "requirements.txt", "pyproject.toml", "poetry.lock", "go.mod", "go.sum",
    "pom.xml", "build.gradle", "build.gradle.kts", "Cargo.toml", "Cargo.lock",
    "Gemfile", "Gemfile.lock", "composer.json", "composer.lock",
}
SECURITY_HINTS = ("auth", "login", "session", "jwt", "token", "password", "payment", "billing", "checkout", "permission", "security")
API_HINTS = ("route", "routes", "controller", "controllers", "api", "handler", "handlers", "middleware", "service", "services")


def _ext(path: str) -> str:
    if "." not in path:
        return ""
    return "." + path.rsplit(".", 1)[-1].lower()


def _base(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def triage_pr(changed_paths: list[str], changed_files: list[dict] | None = None, policy: dict | None = None) -> QATriageResult:
    paths = [p for p in changed_paths if p]
    if not paths:
        return QATriageResult(
            risk_level="low",
            categories=["no_code_changes"],
            required_agents=[],
            advisory_agents=[],
            reason="No changed files were available for QA triage.",
        )

    lowered = [p.lower() for p in paths]
    categories: list[str] = []

    docs_assets_only = all(_ext(p) in DOC_EXTS | ASSET_EXTS for p in lowered)
    test_only = all(("test" in p or "spec" in p) for p in lowered)
    dependency_change = any(_base(p) in DEPENDENCY_FILES for p in lowered)
    security_change = any(any(hint in p for hint in SECURITY_HINTS) for p in lowered)
    api_change = any(any(hint in p for hint in API_HINTS) for p in lowered)

    if docs_assets_only:
        categories.append("docs_assets_only")
        return QATriageResult(
            risk_level="low",
            categories=categories,
            required_agents=[],
            advisory_agents=["static_analysis"],
            reason="Only documentation or static asset files changed.",
        )

    if test_only:
        categories.append("test_only")
        return QATriageResult(
            risk_level="low",
            categories=categories,
            required_agents=["regression"],
            advisory_agents=[],
            reason="Only test/spec files changed.",
        )

    required = ["static_analysis", "regression", "vapt"]
    advisory = ["functionality"]
    risk = "medium"

    if dependency_change:
        categories.append("dependency_change")
    if security_change:
        categories.append("security_sensitive")
        risk = "high"
        advisory.extend(["performance"])
    if api_change:
        categories.append("api_or_service_change")
        risk = "high"
    if not categories:
        categories.append("code_change")

    if policy and policy.get("stress_enabled") and risk == "high":
        advisory.append("stress_test")

    return QATriageResult(
        risk_level=risk,
        categories=categories,
        required_agents=list(dict.fromkeys(required)),
        advisory_agents=list(dict.fromkeys(advisory)),
        reason=f"Detected {', '.join(categories)} across {len(paths)} changed file(s).",
    )
