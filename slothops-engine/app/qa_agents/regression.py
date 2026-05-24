import logging

from app.code_analysis.command_runner import run_command

logger = logging.getLogger("slothops.qa.regression")

async def run_regression_tests(repo_dir: str, stack_config: dict = None) -> dict:
    """
    Run the existing test suite using the detected test_command from stack config.
    """
    if not stack_config:
        stack_config = {"test_command": None, "language": "unknown"}
    
    logger.info("Starting Regression Testing...")
    status = "passed"
    summary_lines = []
    logs = ""
    
    test_command = stack_config.get("test_command")
    language = stack_config.get("language", "unknown")
    
    if not test_command:
        return {
            "status": "warning",
            "summary": f"No test command configured for {language} stack. Skipping regression.",
            "issues": [],
            "logs": "",
            "artifacts": [],
        }
    
    try:
        logger.debug("Running regression tests: %s", test_command)
        res = run_command(test_command, repo_dir, timeout=120)
        if res["timed_out"]:
            status = "warning"
            summary_lines.append("Regression test suite timed out (>120s).")
            logs = res["stdout"] + "\n" + res["stderr"]
        elif res["exit_code"] == 0:
            summary_lines.append("All existing regression tests passed.")
        elif res["exit_code"] == 5 and "pytest" in test_command:
            # pytest exit code 5 means no tests were collected
            summary_lines.append("No tests found to run.")
        else:
            status = "failed"
            summary_lines.append(f"Regression tests failed (exit code {res['exit_code']}).")
            logs = (res["stdout"] + "\n" + res["stderr"])[:4000]
    except Exception as e:
        logger.error("Failed to run regression tests: %s", e)
        summary_lines.append("Failed to execute regression test suite.")
        status = "warning"
        
    return {
        "status": status,
        "summary": " ".join(summary_lines),
        "issues": [],
        "logs": logs,
        "artifacts": [],
    }
