import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

import llm_fixer
from models import IssueRecord


def _fix_payload():
    return {
        "root_cause": "Null user was not handled.",
        "confidence": "high",
        "files_changed": [
            {
                "path": "src/users.ts",
                "original_content": "old",
                "fixed_content": "new",
                "explanation": "Handle null user.",
            }
        ],
        "generated_tests": [
            {
                "path": "tests/users.test.ts",
                "original_content": "",
                "fixed_content": "test",
                "explanation": "Covers null user.",
            }
        ],
        "pr_title": "fix: handle null user",
        "pr_body": "Generated fix",
        "deep_scan_needed": False,
        "deep_scan_files": [],
    }


def test_extract_json_object_from_markdown():
    raw = "```json\n" + json.dumps({"ok": True}) + "\n```"
    assert llm_fixer.extract_json_object(raw) == {"ok": True}


@pytest.mark.asyncio
async def test_generate_fix_awaits_provider_and_parses_json(monkeypatch):
    calls = []

    async def fake_generate_with_fallback(**kwargs):
        calls.append(kwargs)
        return json.dumps(_fix_payload()), "fake-model"

    monkeypatch.setattr(llm_fixer, "generate_with_fallback", fake_generate_with_fallback)
    issue = IssueRecord(
        id="issue1",
        error_type="TypeError",
        error_message="Cannot read user",
        file_path="src/users.ts",
        function_name="getUser",
        line_number=10,
        stack_trace="trace",
    )

    fix = await llm_fixer.generate_fix(issue, {"src/users.ts": "const user = null"})

    assert calls
    assert fix.root_cause == "Null user was not handled."
    assert fix.files_changed[0].path == "src/users.ts"
