import json
import logging
import os
import subprocess
from google import genai
from google.genai import types

logger = logging.getLogger("slothops.qa.functionality")

FUNCTIONALITY_TEST_PROMPT = """
You are an expert QA Engineer. 
I will provide you with a set of changed files from a Pull Request.
Your job is to write a single generic unit test file that tests the core functionality of the new changes.
If the repository uses TypeScript/JavaScript, write a Jest/Mocha test file (e.g. `qa_functionality.test.ts`).
If Python, write a pytest file (e.g. `test_qa_functionality.py`).

Output ONLY valid JSON in the following format, with no markdown formatting around it:
{
    "tests": [
        {
            "path": "test_qa_functionality.py",
            "content": "import pytest\\n\\ndef test_something():\\n    pass"
        }
    ]
}

CHANGED FILES:
{changed_files}
"""

async def run_functionality_tests(
    repo_dir: str, 
    changed_files: list[dict], 
    gemini_api_key: str
) -> dict:
    """
    1. Ask Gemini to generate test cases for the changed files
    2. Write them to repo_dir
    3. Run the tests
    """
    if not changed_files:
        return {"status": "passed", "summary": "No changed files to test."}
        
    logger.info("Functionality QA: Generating test cases via Gemini...")
    client = genai.Client(api_key=gemini_api_key)
    
    files_str = ""
    for cf in changed_files:
        files_str += f"\n--- {cf.get('path')} ---\n{cf.get('content')}\n"
        
    prompt = FUNCTIONALITY_TEST_PROMPT.format(changed_files=files_str)
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
        )
        resp_text = response.text.strip()
        if resp_text.startswith("```json"):
            resp_text = resp_text[7:-3].strip()
        elif resp_text.startswith("```"):
            resp_text = resp_text[3:-3].strip()
            
        data = json.loads(resp_text)
        tests = data.get("tests", [])
    except Exception as e:
        logger.error("Failed to generate functionality tests: %s", e)
        return {"status": "warning", "summary": f"Failed to generate tests via LLM: {e}"}
        
    if not tests:
        return {"status": "passed", "summary": "LLM decided no functionality tests were needed."}
        
    # Write the tests
    test_paths = []
    for t in tests:
        t_path = os.path.join(repo_dir, t["path"])
        os.makedirs(os.path.dirname(t_path), exist_ok=True)
        with open(t_path, "w") as f:
            f.write(t["content"])
        test_paths.append(t["path"])
        
    # Run them
    logger.info("Functionality QA: Running tests %s", test_paths)
    
    # Simple heuristic to run tests based on file extension
    first_test = test_paths[0]
    if first_test.endswith(".ts") or first_test.endswith(".js"):
        cmd = ["npx", "jest", "--passWithNoTests"] + test_paths
    elif first_test.endswith(".py"):
        cmd = ["python", "-m", "pytest"] + test_paths
    else:
        # Fallback
        return {"status": "warning", "summary": f"Unknown test framework for {first_test}"}
        
    try:
        res = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
        if res.returncode == 0:
            return {
                "status": "passed",
                "summary": f"Generated {len(test_paths)} test files. All passed successfully."
            }
        else:
            return {
                "status": "failed",
                "summary": f"Generated test failed.\n\nOutput:\n{res.stdout[:500]}",
                "failures": res.stdout[:1000]
            }
    except Exception as e:
        logger.error("Functionality test execution failed: %s", e)
        return {"status": "warning", "summary": f"Failed to execute test runner: {e}"}
