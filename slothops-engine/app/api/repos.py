"""Repos router.

Owns repo listing (GitHub App + local config join), policy editing,
and preflight readiness checks. Paths match the legacy main.py routes.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends

from app import database as db
from app.core.config import load_settings
from app.core.security import get_current_workspace
from app.models import AuditAction, AuditEvent, RepoConfig, RepoConfigRequest

logger = logging.getLogger("slothops.api.repos")

router = APIRouter(tags=["repos"])


# Per-workspace cache of GitHub repo lists. 5-minute TTL, mirrors the
# previous behavior in main.py.
_repos_cache: dict[str, tuple[list, float]] = {}
_REPOS_CACHE_TTL = 300


def _invalidate_repos_cache(workspace_id: str) -> None:
    _repos_cache.pop(workspace_id, None)


@router.get("/api/repos")
async def list_repos(workspace_id: str = Depends(get_current_workspace)):
    """List repos accessible to the GitHub App installation, enriched
    with SlothOps config state. Cached 5 minutes per workspace.
    """
    settings = load_settings()
    cached = _repos_cache.get(workspace_id)
    if cached and (time.time() - cached[1]) < _REPOS_CACHE_TTL:
        return {"repos": cached[0], "cached": True}

    integration = await db.get_integration(workspace_id, settings.database_path)
    if not integration or not integration.github_installation_id:
        return {
            "repos": [],
            "github_connected": False,
            "message": "GitHub App not linked. Use /api/github/link.",
        }
    try:
        from app.integrations.github_app import get_integration as _get_gh_integration
        gi = _get_gh_integration(settings.github_app_id, settings.github_app_private_key)
        inst = gi.get_app_installation(int(integration.github_installation_id))
        gh_repos = list(inst.get_repos())
    except Exception as e:
        logger.warning("Could not fetch repos for workspace %s: %s", workspace_id, e)
        return {"repos": [], "error": str(e)}

    repo_configs_list = await db.list_repo_configs(workspace_id, settings.database_path)
    config_map = {rc.repo_name: rc for rc in repo_configs_list}

    result = []
    for repo in gh_repos:
        rc = config_map.get(repo.full_name)
        result.append({
            "full_name": repo.full_name,
            "private": repo.private,
            "default_branch": repo.default_branch,
            "language": repo.language,
            "url": repo.html_url,
            "slothops": {
                "configured": rc is not None,
                "active": rc.active if rc else False,
                "sentry_mapped": bool(rc.sentry_project_slug) if rc else False,
                "policy_set": bool(rc.config_json) if rc else False,
            },
        })
    result.sort(key=lambda r: (not r["slothops"]["active"], r["full_name"]))
    _repos_cache[workspace_id] = (result, time.time())
    return {"repos": result, "total": len(result), "github_connected": True}


@router.post("/api/repos/config")
async def upsert_repo_config_endpoint(
    req: RepoConfigRequest,
    workspace_id: str = Depends(get_current_workspace),
):
    """Create or update a repo's SlothOps policy."""
    settings = load_settings()
    existing = await db.get_repo_config(workspace_id, req.repo_name, settings.database_path)
    audit_action = (
        AuditAction.REPO_CONFIG_UPDATED if existing else AuditAction.REPO_CONFIG_CREATED
    )

    config = RepoConfig(
        workspace_id=workspace_id,
        repo_name=req.repo_name,
        config_json={
            "default_branch": req.default_branch,
            "rollback_mode": req.rollback_mode,
            "rollback_strategy": req.rollback_strategy,
            "required_agents": req.required_agents,
            "advisory_agents": req.advisory_agents,
            "warnings_block_merge": req.warnings_block_merge,
            "allowed_environments": req.allowed_environments,
            "max_resolution_attempts": req.max_resolution_attempts,
            "stress_enabled": req.stress_enabled,
        },
        sentry_project_slug=req.sentry_project_slug,
        active=req.active,
    )
    await db.upsert_repo_config(config, settings.database_path)
    _invalidate_repos_cache(workspace_id)
    await db.create_audit_event(AuditEvent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        repo_name=req.repo_name,
        action=audit_action.value,
        target_type="repo_config",
        target_id=req.repo_name,
        metadata_json={
            "sentry_project_slug": req.sentry_project_slug,
            "active": req.active,
            "rollback_mode": req.rollback_mode,
        },
    ), settings.database_path)
    return {"status": "saved", "repo_name": req.repo_name, "action": audit_action.value}


@router.get("/api/repos/{owner}/{repo}/policy")
async def get_repo_policy(
    owner: str,
    repo: str,
    workspace_id: str = Depends(get_current_workspace),
):
    """Return the effective merged policy (defaults + repo overrides)."""
    from app.policy import get_effective_policy

    settings = load_settings()
    repo_name = f"{owner}/{repo}"
    policy = await get_effective_policy(workspace_id, repo_name, settings.database_path)
    repo_config = await db.get_repo_config(workspace_id, repo_name, settings.database_path)
    return {
        "repo_name": repo_name,
        "policy": policy,
        "has_overrides": repo_config is not None,
        "sentry_project_slug": repo_config.sentry_project_slug if repo_config else None,
        "active": repo_config.active if repo_config else False,
    }


@router.post("/api/repos/{owner}/{repo}/preflight")
async def run_preflight(
    owner: str,
    repo: str,
    workspace_id: str = Depends(get_current_workspace),
):
    """Non-destructive readiness check — returns structured pass/warning/fail results."""
    from app.models import PreflightCheck

    settings = load_settings()
    repo_name = f"{owner}/{repo}"
    checks: list[PreflightCheck] = []

    # 1. GitHub App linked
    integration = await db.get_integration(workspace_id, settings.database_path)
    if not integration or not integration.github_installation_id:
        checks.append(PreflightCheck(
            check="github_app_linked", status="failed",
            reason="GitHub App not linked.",
            next_action="Install the SlothOps bot and call POST /api/github/link.",
        ))
        return {
            "repo_name": repo_name,
            "overall": "failed",
            "checks": [c.model_dump() for c in checks],
        }
    checks.append(PreflightCheck(
        check="github_app_linked", status="passed",
        reason=f"Installation {integration.github_installation_id} linked.",
    ))

    # 2. Repo accessible + default branch
    repo_obj = None
    try:
        from app.integrations.github_app import get_repo_for_installation
        repo_obj, _ = get_repo_for_installation(
            settings.github_app_id, settings.github_app_private_key,
            integration.github_installation_id, repo_name,
        )
        checks.append(PreflightCheck(
            check="repo_accessible", status="passed",
            reason=f"{repo_name} is accessible.",
        ))
        try:
            repo_obj.get_branch(repo_obj.default_branch)
            checks.append(PreflightCheck(
                check="default_branch", status="passed",
                reason=f"Default branch '{repo_obj.default_branch}' exists.",
            ))
        except Exception as be:
            checks.append(PreflightCheck(
                check="default_branch", status="failed",
                reason=f"Branch check failed: {be}",
                next_action="Ensure the repo has at least one commit.",
            ))
    except Exception as e:
        checks.append(PreflightCheck(
            check="repo_accessible", status="failed",
            reason=f"Cannot access {repo_name}: {e}",
            next_action="Ensure the GitHub App is installed on this repo.",
        ))

    # 3. GitHub App permissions
    try:
        from app.integrations.github_app import get_integration as _ghi
        gi = _ghi(settings.github_app_id, settings.github_app_private_key)
        inst = gi.get_app_installation(int(integration.github_installation_id))
        perms = inst.raw_data.get("permissions", {})
        statuses_ok = perms.get("statuses") in ("write", "admin")
        prs_ok = perms.get("pull_requests") in ("write", "admin")
        if statuses_ok and prs_ok:
            checks.append(PreflightCheck(
                check="github_permissions", status="passed",
                reason="App has commit status and PR write permissions.",
            ))
        else:
            missing = (["commit statuses"] if not statuses_ok else []) + \
                      (["pull requests"] if not prs_ok else [])
            checks.append(PreflightCheck(
                check="github_permissions", status="warning",
                reason=f"Missing permissions: {', '.join(missing)}.",
                next_action="Re-install GitHub App with required permissions.",
            ))
    except Exception as e:
        checks.append(PreflightCheck(
            check="github_permissions", status="warning",
            reason=f"Could not verify permissions: {e}",
        ))

    # 4. .slothops.yml detection
    if repo_obj:
        try:
            repo_obj.get_contents(".slothops.yml")
            checks.append(PreflightCheck(
                check="stack_config", status="passed",
                reason=".slothops.yml found — custom stack config will be used.",
            ))
        except Exception:
            checks.append(PreflightCheck(
                check="stack_config", status="warning",
                reason="No .slothops.yml — stack will be auto-detected.",
                next_action="Optionally add .slothops.yml to specify test/lint commands.",
            ))

    # 5. Sentry mapping
    repo_config = await db.get_repo_config(workspace_id, repo_name, settings.database_path)
    if repo_config and repo_config.sentry_project_slug:
        checks.append(PreflightCheck(
            check="sentry_mapping", status="passed",
            reason=f"Sentry project '{repo_config.sentry_project_slug}' mapped.",
        ))
    else:
        checks.append(PreflightCheck(
            check="sentry_mapping", status="warning",
            reason="No Sentry project slug configured.",
            next_action="Set sentry_project_slug via POST /api/repos/config, or skip if not using Sentry.",
        ))

    # 6. Rollback strategy safety
    cfg_json = repo_config.config_json if repo_config else {}
    mode = cfg_json.get("rollback_mode", "approval_required")
    strategy = cfg_json.get("rollback_strategy", "rollback_pr")
    if mode == "approval_required" and strategy == "rollback_pr":
        checks.append(PreflightCheck(
            check="rollback_safety", status="passed",
            reason="Safe defaults: approval_required + rollback_pr.",
        ))
    elif mode in ("auto_revert",) or strategy == "direct_revert":
        checks.append(PreflightCheck(
            check="rollback_safety", status="warning",
            reason=f"Aggressive rollback: mode='{mode}', strategy='{strategy}'.",
            next_action="Confirm intentional. Recommend approval_required + rollback_pr for new setups.",
        ))
    else:
        checks.append(PreflightCheck(
            check="rollback_safety", status="passed",
            reason=f"Rollback: mode='{mode}', strategy='{strategy}'.",
        ))

    statuses = [c.status for c in checks]
    overall = "failed" if "failed" in statuses else "warning" if "warning" in statuses else "passed"

    await db.create_audit_event(AuditEvent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        repo_name=repo_name,
        action=AuditAction.PREFLIGHT_RUN.value,
        target_type="repo",
        target_id=repo_name,
        metadata_json={"overall": overall, "checks": len(checks)},
    ), settings.database_path)

    return {
        "repo_name": repo_name,
        "overall": overall,
        "checks": [c.model_dump() for c in checks],
    }
