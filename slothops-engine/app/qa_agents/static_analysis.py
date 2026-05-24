import logging

from app.code_analysis.command_runner import run_command

logger = logging.getLogger("slothops.qa.static_analysis")

async def run_static_analysis(repo_dir: str, changed_files: list[str], stack_config: dict = None) -> dict:
    """
    Run static analysis on the cloned repo using the detected stack config.
    Falls back to basic heuristic if no config is provided.
    """
    if not stack_config:
        stack_config = {"language": "unknown", "lint_commands": [], "type_check_command": None}
    
    language = stack_config.get("language", "unknown")
    lint_commands = stack_config.get("lint_commands", [])
    type_check_cmd = stack_config.get("type_check_command")
    
    logger.info("Static analysis for stack: language=%s", language)
    
    status = "passed"
    issues = []
    summary_lines = []
    
    # 1. Run type checker if available
    if type_check_cmd:
        try:
            logger.debug("Running type checker: %s", type_check_cmd)
            res = run_command(type_check_cmd, repo_dir, timeout=60)
            if res["timed_out"]:
                status = "warning"
                summary_lines.append("Type checking timed out (>60s).")
            elif res["exit_code"] != 0:
                status = "warning"
                summary_lines.append(f"Type checker reported errors.")
                out_text = res["stdout"].strip() or res["stderr"].strip()
                issues.append({"tool": type_check_cmd.split()[0], "output": out_text[:2000] + ("..." if len(out_text) > 2000 else "")})
            else:
                summary_lines.append("Type checking passed.")
        except Exception as e:
            logger.error("Failed to run type checker: %s", e)
    
    # 2. Run linters
    for lint_cmd in lint_commands:
        try:
            logger.debug("Running linter: %s", lint_cmd)
            res = run_command(lint_cmd, repo_dir, timeout=60)
            if res["timed_out"]:
                status = "warning"
                summary_lines.append(f"Linter timed out (>60s).")
            elif res["exit_code"] != 0:
                status = "warning"
                tool_name = lint_cmd.split()[0]
                summary_lines.append(f"{tool_name} reported warnings or errors.")
                out_text = res["stdout"].strip() or res["stderr"].strip()
                issues.append({"tool": tool_name, "output": out_text[:2000] + ("..." if len(out_text) > 2000 else "")})
            else:
                tool_name = lint_cmd.split()[0]
                summary_lines.append(f"{tool_name} passed.")
        except Exception as e:
            logger.error("Failed to run linter: %s", e)
            
    if not summary_lines:
        status = "warning"
        summary_lines.append(f"No static analysis tools configured for detected stack ({language}).")
        
    return {
        "status": status,
        "issues": issues,
        "summary": " ".join(summary_lines),
        "logs": "",
        "artifacts": [],
    }
