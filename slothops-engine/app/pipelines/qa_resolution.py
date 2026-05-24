"""AI-assisted resolution for failed QA reports."""

from __future__ import annotations

import json
import logging
import uuid

from app import database as db
from app.llm.client import generate_with_fallback
from app.integrations.github_app import get_repo_for_installation
from app.llm.fixer import extract_json_object
from app.models import AuditAction, AuditEvent
from app.sse_manager import broadcast

logger = logging.getLogger("slothops.qa_resolution")


async def request_qa_resolution(
    report_id: str,
    workspace_id: str,
    db_path: str,
    github_app_id: str | int | None,
    private_key: str | None,
) -> None:
    report = await db.get_qa_report(report_id, db_path)
    if not report or report.workspace_id != workspace_id:
        raise ValueError("QA report not found for workspace")
    await db.create_audit_event(AuditEvent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        repo_name=report.repo_name,
        action=AuditAction.QA_RESOLUTION_REQUESTED.value,
        target_type="qa_report",
        target_id=report.id,
    ), db_path)

    integration = await db.get_integration(workspace_id, db_path)
    if not integration or not integration.github_installation_id:
        await db.update_qa_report(report.id, db_path, overall_status="failed", summary="Resolution failed: GitHub App not connected.")
        return

    repo, _ = get_repo_for_installation(
        github_app_id, private_key, integration.github_installation_id, report.repo_name
    )
    pr = repo.get_pull(report.pr_number)
    pr_branch = pr.head.ref

    code_context = {}
    for f in pr.get_files():
        if f.status == "removed":
            continue
        try:
            content_file = repo.get_contents(f.filename, ref=pr_branch)
            if not isinstance(content_file, list):
                code_context[f.filename] = {
                    "patch": getattr(f, "patch", "No diff available"),
                    "content": content_file.decoded_content.decode("utf-8", errors="replace"),
                }
        except Exception:
            continue

    if not code_context:
        await db.update_qa_report(report.id, db_path, overall_status="failed", summary="Resolution failed: no code files found in PR.")
        return

    error_context = _build_error_context(report)
    files_section = "\n".join(
        f"--- FILE: {path} ---\nDIFF:\n{data['patch']}\nFULL CONTENT:\n{data['content'][:8000]}"
        for path, data in code_context.items()
    )
    prompt = f"""Resolve QA failures for this PR.

Rules:
1. Output only JSON.
2. Commit fixes only for files that are required to address the QA failures.
3. Return complete file contents.

QA failures:
{error_context}

PR files:
{files_section}

JSON shape:
{{
  "fixes": [{{"path": "relative/path", "fixed_content": "complete content", "explanation": "why"}}],
  "skip_reasons": [{{"agent": "name", "reason": "why"}}],
  "commit_message": "fix: resolve QA failures"
}}
"""
    try:
        raw, _ = await generate_with_fallback(prompt=prompt, response_mime_type="application/json")
        fix_data = extract_json_object(raw)
    except Exception as exc:
        await db.update_qa_report(report.id, db_path, overall_status="failed", summary=f"Resolution failed: LLM error: {exc}")
        return

    fixes = fix_data.get("fixes", [])
    skip_reasons = fix_data.get("skip_reasons", [])
    commit_msg = fix_data.get("commit_message", "fix: resolve QA failures")
    committed = 0
    if fixes:
        from github import InputGitTreeElement

        elements = []
        for fix in fixes:
            path = fix.get("path", "")
            content = fix.get("fixed_content", "")
            if path and content and not path.startswith("/") and ".." not in path.split("/"):
                elements.append(InputGitTreeElement(path, "100644", "blob", content))
        if elements:
            ref = repo.get_git_ref(f"heads/{pr_branch}")
            latest_commit_sha = ref.object.sha
            base_tree = repo.get_git_tree(latest_commit_sha)
            new_tree = repo.create_git_tree(elements, base_tree)
            parent_commit = repo.get_git_commit(latest_commit_sha)
            new_commit = repo.create_git_commit(commit_msg, new_tree, [parent_commit])
            ref.edit(new_commit.sha)
            committed = len(elements)

    comment = "## SlothOps QA Auto-Resolution\n\n"
    if committed:
        comment += f"Pushed {committed} fix(es) to `{pr_branch}`. QA will re-run on the synchronize event.\n"
    else:
        comment += "No directly fixable changes were committed.\n"
    if skip_reasons:
        comment += "\n### Skipped\n" + "\n".join(f"- **{s.get('agent', 'QA')}**: {s.get('reason', 'Skipped')}" for s in skip_reasons)
    pr.create_issue_comment(comment)

    await db.update_qa_report(report.id, db_path, overall_status="resolved", summary=f"QA resolution committed {committed} fix(es).")
    await broadcast("qa_update", {"id": report.id, "status": "resolved"})


def _build_error_context(report) -> str:
    chunks = []
    for name, data in [
        ("Static Analysis", report.static_analysis),
        ("Functionality", report.functionality),
        ("VAPT", report.vapt),
        ("Stress", report.stress_test),
        ("Regression", report.regression),
        ("Performance", report.performance),
    ]:
        if data and data.get("status") in ("failed", "warning"):
            chunks.append(f"### {name}\nSummary: {data.get('summary', '')}\nIssues: {json.dumps(data.get('issues', []))}\nLogs:\n{data.get('logs', '')[:2000]}")
    return "\n\n".join(chunks)
