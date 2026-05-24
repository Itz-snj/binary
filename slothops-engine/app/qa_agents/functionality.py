import json
import logging
import os

from app.llm.client import generate_with_fallback
from app.code_analysis.command_runner import run_command

logger = logging.getLogger("slothops.qa.functionality")

FUNCTIONALITY_TEST_PROMPT = """
You are an expert QA Engineer. 
I will provide you with a set of changed files from a Pull Request.
The repository uses: {language} with {framework} framework.
Your job is to write a single generic unit test file that tests the core functionality of the new changes.

If {language} is "typescript" or "javascript", write a Jest/Mocha test file.
If {language} is "python", write a pytest file.
If {language} is "go", write a Go test file with `_test.go` suffix.
If {language} is "java", write a JUnit test file.
If {language} is "rust", write a Rust test module.
Otherwise, write the most appropriate test for the language.

Output ONLY valid JSON in the following format, with no markdown formatting around it:
{{
    "tests": [
        {{
            "path": "test_qa_functionality.py",
            "content": "import pytest\\n\\ndef test_something():\\n    pass"
        }}
    ]
}}

CHANGED FILES:
{changed_files}
"""

async def run_functionality_tests(
    repo_dir: str, 
    changed_files: list[dict], 
    stack_config: dict = None
) -> dict:
    """
    1. Ask LLM to generate test cases for the changed files (using detected stack)
    2. Write them to repo_dir
    3. Run the tests
    """
    if not stack_config:
        stack_config = {"language": "unknown", "framework": "unknown", "test_command": None}
    
    if not changed_files:
        return {"status": "passed", "summary": "No changed files to test.", "issues": [], "logs": "", "artifacts": []}
        
    language = stack_config.get("language", "unknown")
    framework = stack_config.get("framework", "unknown")
    test_command = stack_config.get("test_command")
    
    logger.info("Functionality QA: Generating tests for %s/%s stack...", language, framework)
    
    files_str = ""
    for cf in changed_files:
        files_str += f"\n--- {cf.get('path')} ---\n{cf.get('content')}\n"
        
    prompt = FUNCTIONALITY_TEST_PROMPT.format(
        changed_files=files_str, 
        language=language, 
        framework=framework
    )
    
    try:
        resp_text, model_used = await generate_with_fallback(
            prompt=prompt,
        )
        resp_text = resp_text.strip()
        if resp_text.startswith("```json"):
            resp_text = resp_text[7:-3].strip()
        elif resp_text.startswith("```"):
            resp_text = resp_text[3:-3].strip()
            
        data = json.loads(resp_text)
        tests = data.get("tests", [])
    except Exception as e:
        logger.error("Failed to generate functionality tests: %s", e)
        return {"status": "warning", "summary": f"Failed to generate tests via LLM: {e}", "issues": [], "logs": "", "artifacts": []}
        
    if not tests:
        return {"status": "passed", "summary": "LLM decided no functionality tests were needed.", "issues": [], "logs": "", "artifacts": []}
        
    # Write the tests
    test_paths = []
    generated_root = os.path.join(repo_dir, ".slothops", "generated-tests")
    for t in tests:
        raw_path = str(t.get("path", "generated_test.py")).replace("\\", "/")
        if raw_path.startswith("/") or ".." in raw_path.split("/"):
            return {
                "status": "warning",
                "summary": f"Rejected unsafe generated test path: {raw_path}",
                "issues": [{"tool": "functionality", "output": f"Unsafe path: {raw_path}"}],
                "logs": "",
                "artifacts": [],
            }
        safe_name = raw_path.rsplit("/", 1)[-1] or "generated_test.py"
        rel_path = f".slothops/generated-tests/{safe_name}"
        t_path = os.path.join(generated_root, safe_name)
        os.makedirs(os.path.dirname(t_path), exist_ok=True)
        with open(t_path, "w") as f:
            f.write(t["content"])
        test_paths.append(rel_path)
        
    # Run tests using stack-detected test runner
    logger.info("Functionality QA: Running tests %s", test_paths)
    
    # Determine command based on stack config or file extension fallback
    first_test = test_paths[0]
    cmd = None
    
    if language in ("typescript", "javascript"):
        cmd = ["npx", "--yes", "jest", "--passWithNoTests", "--forceExit"] + test_paths
    elif language == "python":
        cmd = ["python", "-m", "pytest"] + test_paths
    elif language == "go":
        cmd = ["go", "test", "./..."]
    elif language == "java":
        # Run via maven or gradle depending on framework
        if framework == "maven":
            cmd = ["mvn", "test"]
        elif framework == "gradle":
            cmd = ["./gradlew", "test"]
    elif language == "rust":
        cmd = ["cargo", "test"]
    else:
        # File extension fallback
        if first_test.endswith((".ts", ".js")):
            cmd = ["npx", "--yes", "jest", "--passWithNoTests"] + test_paths
        elif first_test.endswith(".py"):
            cmd = ["python", "-m", "pytest"] + test_paths
    
    if not cmd:
        return {"status": "warning", "summary": f"No test runner configured for {language} stack.", "issues": [], "logs": "", "artifacts": []}
        
    try:
        res = run_command(cmd, repo_dir, timeout=90)
        output = (res["stdout"] + "\n" + res["stderr"])[:4000]
        if res["timed_out"]:
            return {
                "status": "warning",
                "summary": "Test framework timed out (>90s).",
                "issues": [],
                "logs": output,
                "artifacts": [{"type": "generated_test", "path": p} for p in test_paths],
            }
        if res["exit_code"] == 0:
            return {
                "status": "passed",
                "summary": f"Generated {len(test_paths)} test files. All passed successfully.",
                "issues": [],
                "logs": output,
                "artifacts": [{"type": "generated_test", "path": p} for p in test_paths],
            }
        else:
            return {
                "status": "failed",
                "summary": f"Generated test failed.\n\nOutput:\n{output[:500]}",
                "issues": [{"tool": "generated_tests", "output": output[:1000]}],
                "failures": output[:1000],
                "logs": output,
                "artifacts": [{"type": "generated_test", "path": p} for p in test_paths],
            }
    except Exception as e:
        logger.error("Functionality test execution failed: %s", e)
        return {"status": "warning", "summary": f"Failed to execute test runner: {e}", "issues": [], "logs": str(e), "artifacts": [{"type": "generated_test", "path": p} for p in test_paths]}
