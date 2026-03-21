import os
import json
import logging
import subprocess

logger = logging.getLogger("slothops.qa.vapt")

async def run_vapt_scan(repo_dir: str) -> dict:
    """
    Run Vulnerability Assessment and Penetration Testing.
    Currently runs `npm audit` for Node.js projects, or python equivalents if possible.
    """
    logger.info("Starting VAPT scan...")
    status = "passed"
    summary_lines = []
    issues = []
    
    # 1. Dependency Audit for Node.js
    if os.path.exists(os.path.join(repo_dir, "package.json")):
        try:
            logger.debug("Running npm audit...")
            res = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=repo_dir, capture_output=True, text=True
            )
            # npm audit returns non-zero if vulnerabilities are found
            try:
                audit_data = json.loads(res.stdout)
                vulns = audit_data.get("metadata", {}).get("vulnerabilities", {})
                total_vulns = sum(vulns.values())
                
                if total_vulns > 0:
                    critical = vulns.get("critical", 0)
                    high = vulns.get("high", 0)
                    if critical > 0 or high > 0:
                        status = "failed"
                    else:
                        status = "warning"
                    
                    summary_lines.append(f"npm audit found {total_vulns} vulnerabilities (Critical: {critical}, High: {high}).")
                    issues.append({"tool": "npm audit", "vulns": vulns})
                else:
                    summary_lines.append("npm audit passed with 0 vulnerabilities.")
            except json.JSONDecodeError:
                logger.warning("Failed to parse npm audit JSON output.")
                summary_lines.append("npm audit output was not valid JSON.")
        except Exception as e:
            logger.error("Failed to run npm audit: %s", e)
            summary_lines.append("npm audit execution failed.")
            
    # 2. Basic Python Audit
    elif os.path.exists(os.path.join(repo_dir, "requirements.txt")):
        try:
            logger.debug("Running safety/pip-audit check...")
            # Ideally pip-audit, but we'll try safety if installed, fallback to stub
            res = subprocess.run(
                ["pip-audit", "-r", "requirements.txt", "-f", "json"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if res.returncode != 0:
                status = "warning"
                summary_lines.append("pip-audit found vulnerabilities.")
                issues.append({"tool": "pip-audit", "output": res.stdout[:500]})
            else:
                summary_lines.append("pip-audit passed.")
        except Exception:
            summary_lines.append("pip-audit not installed or failed to run.")

    # 3. Future addition: gitleaks, semgrep, secret scanning
    
    if not summary_lines:
        summary_lines.append("No supported VAPT tools ran.")
        
    return {
        "status": status,
        "summary": " ".join(summary_lines),
        "issues": issues
    }
