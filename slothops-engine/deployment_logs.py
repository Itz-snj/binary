"""Deployment/build log collection helpers."""

from __future__ import annotations


def fetch_deployment_logs(repo, failed_sha: str, fallback: str = "", max_chars: int = 12000) -> dict:
    """Best-effort GitHub Actions log lookup with safe fallback text."""
    text = fallback or "Deployment failed; no detailed logs were provided."
    metadata = {"source": "fallback"}
    try:
        runs = repo.get_workflow_runs(head_sha=failed_sha)
        if runs.totalCount:
            run = runs[0]
            metadata = {"source": "github_actions", "run_id": run.id, "run_url": run.html_url}
            text = f"GitHub Actions run failed: {run.html_url}\nConclusion: {run.conclusion}\nStatus: {run.status}\n"
    except Exception:
        pass
    return {"logs": text[:max_chars], "metadata": metadata}
