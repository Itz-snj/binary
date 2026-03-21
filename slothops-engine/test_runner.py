"""
SlothOps Engine — Test Runner
Clones the target repository to a temporary directory, applies the LLM-generated fixes
and tests, installs dependencies, and runs the test suite.
"""

import os
import subprocess
import tempfile
import logging
from models import LLMFixResponse

logger = logging.getLogger("slothops.test_runner")

def validate_fix(fix: LLMFixResponse, repo, token: str) -> tuple[bool, str]:
    """
    Creates a temporary directory, clones the authenticated repo, applies the fix 
    and generated tests, runs the tests, and returns (success, output_string).
    """
    # 1. Prepare clone URL with installation token
    clone_url = repo.clone_url.replace("https://", f"https://x-access-token:{token}@")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info("Cloning %s into temporary directory for testing...", repo.full_name)
        
        # 2. Shallow clone the repo for speed
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, tmpdir],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error("Failed to clone repo for testing: %s", e.stderr)
            return False, f"Failed to clone repository: {e.stderr}"

        # 3. Apply changes and generated tests
        all_changes = fix.files_changed + fix.generated_tests
        for change in all_changes:
            target_path = os.path.join(tmpdir, change.path)
            # Ensure directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w") as f:
                f.write(change.fixed_content)

        # 4. Detect framework and run tests
        output = ""
        success = False
        
        try:
            if os.path.exists(os.path.join(tmpdir, "package.json")):
                logger.info("Detected Node.js project. Running npm install && npm test...")
                install_proc = subprocess.run(
                    ["npm", "install"], cwd=tmpdir, capture_output=True, text=True, check=True
                )
                test_proc = subprocess.run(
                    ["npm", "test"], cwd=tmpdir, capture_output=True, text=True
                )
                output = test_proc.stdout + "\n" + test_proc.stderr
                success = (test_proc.returncode == 0)
                
            elif os.path.exists(os.path.join(tmpdir, "requirements.txt")):
                logger.info("Detected Python project. Running pytest...")
                subprocess.run(
                    ["python", "-m", "venv", ".venv"], cwd=tmpdir, capture_output=True, check=True
                )
                pip_path = os.path.join(tmpdir, ".venv", "bin", "pip")
                pytest_path = os.path.join(tmpdir, ".venv", "bin", "pytest")
                
                subprocess.run(
                    [pip_path, "install", "-r", "requirements.txt"], cwd=tmpdir, capture_output=True, check=True
                )
                test_proc = subprocess.run(
                    [pytest_path], cwd=tmpdir, capture_output=True, text=True
                )
                output = test_proc.stdout + "\n" + test_proc.stderr
                success = (test_proc.returncode == 0)
            else:
                return False, "Could not detect test framework (missing package.json or requirements.txt)"
                
        except subprocess.CalledProcessError as e:
            output = f"Command failed during setup: {e.cmd}\n{e.stderr}"
            success = False
        
        # Truncate output to prevent massive context explosion in the LLM prompt
        if len(output) > 4000:
            output = output[:4000] + "\n...[OUTPUT TRUNCATED]..."
            
        return success, output
