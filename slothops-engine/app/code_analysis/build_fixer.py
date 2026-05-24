"""LLM fixer for build and deployment failures."""

from __future__ import annotations

import json
import logging

from app.llm.client import generate_with_fallback
from app.llm.fixer import extract_json_object
from app.models import BuildFixResponse

logger = logging.getLogger("slothops.build_fixer")

SYSTEM = """You are SlothOps Build Fixer. Fix deployment/build failures by changing the root cause.
Return only JSON matching the requested schema. Return complete file contents."""


async def generate_build_fix(
    build_logs: str,
    code_context: dict[str, str],
    stack_config: dict,
    failed_sha: str,
    attempt_number: int,
) -> BuildFixResponse:
    files = "\n\n".join(f"--- {path} ---\n{content[:8000]}" for path, content in code_context.items())
    prompt = f"""FAILED SHA: {failed_sha}
ATTEMPT: {attempt_number}
STACK: {json.dumps(stack_config)}

BUILD LOGS:
{build_logs}

FILES:
{files}

JSON schema:
{{
  "root_cause": "why the deployment failed",
  "confidence": "high|medium|low",
  "files_changed": [{{"path": "file", "fixed_content": "complete content", "explanation": "why"}}],
  "generated_tests": [{{"path": "file", "fixed_content": "complete content", "explanation": "why"}}],
  "pr_title": "fix: ...",
  "pr_body": "markdown"
}}
"""
    raw, _ = await generate_with_fallback(prompt=prompt, system_instruction=SYSTEM, response_mime_type="application/json")
    return BuildFixResponse(**extract_json_object(raw))
