import os
import json
import logging
import subprocess

logger = logging.getLogger("slothops.qa.static_analysis")

def detect_tech_stack(repo_dir: str) -> dict:
    """Very rudimentary tech stack detector based on files in root."""
    stack = {"language": "unknown", "package_manager": "unknown"}
    if os.path.exists(os.path.join(repo_dir, "package.json")):
        stack["package_manager"] = "npm"
        if os.path.exists(os.path.join(repo_dir, "tsconfig.json")):
            stack["language"] = "typescript"
        else:
            stack["language"] = "javascript"
    elif os.path.exists(os.path.join(repo_dir, "requirements.txt")) or os.path.exists(os.path.join(repo_dir, "pyproject.toml")):
        stack["language"] = "python"
        stack["package_manager"] = "pip"
    return stack

async def run_static_analysis(repo_dir: str, changed_files: list[str]) -> dict:
    """
    Run static analysis on the cloned repo.
    We return a dict with status and details.
    """
    stack = detect_tech_stack(repo_dir)
    logger.info("Detected tech stack: %s", stack)
    
    status = "passed"
    issues = []
    summary_lines = []
    
    # Simple typescript/javascript linting check
    if stack["package_manager"] == "npm":
        try:
            # We assume npm install was already run by the orchestrator
            pass
        except Exception:
            pass
            
        # Run TSC if typescript
        if stack["language"] == "typescript":
            try:
                # Run `npx tsc --noEmit`
                logger.debug("Running TSC type checking...")
                res = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=repo_dir, capture_output=True, text=True
                )
                if res.returncode != 0:
                    status = "warning"
                    summary_lines.append("TypeScript compiler found errors.")
                    # We just record the raw output for simplicity in Phase 1
                    issues.append({"tool": "tsc", "output": res.stdout[:500] + ("..." if len(res.stdout)>500 else "")})
                else:
                    summary_lines.append("TypeScript compilation passed.")
            except Exception as e:
                logger.error("Failed to run TSC: %s", e)
        
        # Run ESLint
        try:
            logger.debug("Running ESLint...")
            res = subprocess.run(
                ["npx", "eslint", ".", "--ext", ".ts,.js,.tsx,.jsx"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if res.returncode != 0:
                status = "warning"
                summary_lines.append("ESLint reported warnings or errors.")
                issues.append({"tool": "eslint", "output": res.stdout[:500] + ("..." if len(res.stdout)>500 else "")})
            else:
                summary_lines.append("ESLint passed without issues.")
        except Exception as e:
            logger.error("Failed to run ESLint: %s", e)
            
    elif stack["language"] == "python":
        try:
            logger.debug("Running flake8...")
            res = subprocess.run(
                ["python", "-m", "flake8", "."],
                cwd=repo_dir, capture_output=True, text=True
            )
            if res.returncode != 0:
                status = "warning"
                summary_lines.append("Flake8 reported issues.")
                issues.append({"tool": "flake8", "output": res.stdout[:500] + ("..." if len(res.stdout)>500 else "")})
            else:
                summary_lines.append("Flake8 passed.")
        except Exception:
            pass
            
    if not summary_lines:
        summary_lines.append("No automated analysis tools found/configured for this stack.")
        
    return {
        "status": status,
        "issues": issues,
        "summary": " ".join(summary_lines)
    }
