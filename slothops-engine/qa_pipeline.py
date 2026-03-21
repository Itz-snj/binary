import asyncio
import logging
import os
import tempfile
import subprocess
from datetime import datetime

import database as db
from models import QAReport, QAStatus

from qa_agents.static_analysis import run_static_analysis
from qa_agents.functionality import run_functionality_tests
from github_automation import post_qa_report_comment

logger = logging.getLogger("slothops.qa_pipeline")

async def run_qa_pipeline(
    payload: dict,
    workspace_id: str,
    gemini_api_key: str,
    github_app_id: int,
    github_app_private_key: str,
    db_path: str
):
    """
    Main QA orchestrator. Triggers upon PR close/merge.
    Downloads the merged state, runs the sub-agents sequentially (Phase 1),
    and stores/posts the results.
    """
    from github import Github, GithubIntegration
    
    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        return
        
    pr_number = payload["pull_request"]["number"]
    pr_url = payload["pull_request"]["html_url"]
    repo_name = payload["repository"]["full_name"]
    # The merge commit SHA or branch HEAD
    commit_sha = payload["pull_request"].get("merge_commit_sha") or payload["pull_request"]["head"]["sha"]
    
    logger.info("🚀 Starting QA Pipeline for PR #%s in %s...", pr_number, repo_name)
    
    try:
        integration = GithubIntegration(github_app_id, github_app_private_key)
        access_token = integration.get_access_token(installation_id).token
        gh = Github(access_token)
        repo = gh.get_repo(repo_name)
    except Exception as e:
        logger.error("Failed to auth GitHub App for QA: %s", e)
        return
        
    # 1. Create a running QA Record in DB
    report_id = f"qa-{pr_number}-{commit_sha[:8]}"
    report = QAReport(
        id=report_id,
        workspace_id=workspace_id,
        pr_number=pr_number,
        pr_url=pr_url,
        commit_sha=commit_sha,
        repo_name=repo_name,
        overall_status=QAStatus.RUNNING.value,
        summary="QA tests are currently running..."
    )
    await db.create_qa_report(report, db_path)
    
    # 2. Clone repo locally in a sandbox
    # Using the standard mechanism tested in `test_runner.py`
    clone_url = repo.clone_url.replace("https://", f"https://x-access-token:{access_token}@")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("🧪 QA Sandbox: Cloning %s @ %s...", repo_name, commit_sha)
        try:
            # We clone the specific PR branch/merge commit 
            subprocess.run(
                ["git", "clone", clone_url, tmpdir],
                check=True, capture_output=True, text=True
            )
            subprocess.run(
                ["git", "checkout", commit_sha],
                cwd=tmpdir, check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error("QA Sandbox Failed to clone: %s", e.stderr)
            await db.update_qa_report(report_id, db_path, overall_status=QAStatus.FAILED.value, summary=f"Failed to setup QA sandbox. Clone error.")
            return

        # Next, try to install dependencies if package.json exists
        if os.path.exists(os.path.join(tmpdir, "package.json")):
            logger.info("🧪 QA Sandbox: Running npm install...")
            try:
                subprocess.run(["npm", "install", "--include=dev"], cwd=tmpdir, capture_output=True, text=True)
            except Exception:
                pass
                
        # Additionally, we need to know what files were changed in the PR 
        # to generate specifically targeted functionality tests.
        pr = repo.get_pull(pr_number)
        gh_files = pr.get_files()
        changed_files = []
        changed_paths = []
        for f in gh_files:
            if f.status == "removed":
                continue
            changed_paths.append(f.filename)
            try:
                content_file = repo.get_contents(f.filename, ref=commit_sha)
                if not isinstance(content_file, list):
                    changed_files.append({
                        "path": f.filename,
                        "content": content_file.decoded_content.decode("utf-8", errors="replace")
                    })
            except Exception:
                pass
                
        # 3. Static Analysis Layer
        logger.info("🛠️ Running Static Analysis Agent...")
        static_res = await run_static_analysis(tmpdir, changed_paths)
        report.static_analysis = static_res
        
        # 4. Functionality Layer
        logger.info("🛠️ Running Functionality Agent...")
        func_res = await run_functionality_tests(tmpdir, changed_files, gemini_api_key)
        report.functionality = func_res
        
        # Aggregate status
        final_status = QAStatus.PASSED.value
        if static_res.get("status") == "failed" or func_res.get("status") == "failed":
            final_status = QAStatus.FAILED.value
        elif static_res.get("status") == "warning" or func_res.get("status") == "warning":
            final_status = QAStatus.WARNING.value
            
        report.overall_status = final_status
        report.summary = (
            f"**Static Analysis:** {static_res.get('summary', 'Skipped')}\\n"
            f"**Functionality:** {func_res.get('summary', 'Skipped')}"
        )
        
        # 5. Database update
        await db.update_qa_report(
            report_id, 
            db_path, 
            overall_status=final_status,
            summary=report.summary,
            static_analysis=report.static_analysis,
            functionality=report.functionality
        )
        
        # 6. Post PR Comment
        post_qa_report_comment(pr_url, report.model_dump(), repo, repo_name)
        logger.info("✅ QA Pipeline completed for PR #%s -> Status: %s", pr_number, final_status)
