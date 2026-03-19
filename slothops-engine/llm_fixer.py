"""
SlothOps Engine — LLM Fixer
Constructs prompts, calls OpenAI GPT-4o, and parses the JSON response
into a validated LLMFixResponse.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from openai import OpenAI

from models import IssueRecord, LLMFixResponse
from redactor import redact

logger = logging.getLogger("slothops.llm_fixer")

# ── System prompt (exact copy from AI_CONTEXT.md) ───────────────────────

SYSTEM_PROMPT = """You are SlothOps, an automated production bug remediation system.

RULES:
1. You MUST fix the root cause, not hide the symptom.
2. You MUST NOT wrap code in empty try/catch blocks.
3. You MUST NOT suppress or swallow errors silently.
4. You MUST NOT remove existing error logging or monitoring.
5. You MUST NOT comment out failing code.
6. You MUST NOT add generic fallbacks without clear reasoning.
7. You MUST preserve the original code style and conventions.
8. You MUST explain your root cause hypothesis clearly.
9. If the fix requires changes to multiple files, specify each file separately.
10. If you are not confident about the fix, set confidence to "low"
    and explain why.
11. You MUST return valid JSON matching the specified format.
12. You MUST return the COMPLETE file content for each changed file,
    not just the diff or snippet.

RESPONSE FORMAT (strict JSON):
{
  "root_cause": "one paragraph explanation of why this bug happens",
  "confidence": "high | medium | low",
  "files_changed": [
    {
      "path": "src/routes/users.ts",
      "original_content": "full original file content",
      "fixed_content": "full fixed file content",
      "explanation": "what was changed and why"
    }
  ],
  "pr_title": "fix: short description of the fix",
  "pr_body": "markdown formatted PR description"
}"""


def _build_user_prompt(
    issue: IssueRecord,
    code_context: dict[str, str],
    previous_pr_url: Optional[str] = None,
) -> str:
    """Build the user prompt from the template in AI_CONTEXT.md."""
    # Redact the stack trace before including it
    redacted_trace = redact(issue.stack_trace or "")

    # Main file content
    main_file_path = issue.file_path or "unknown"
    main_content = code_context.get(main_file_path, "File content not available")

    # Related files (everything except main and test)
    related_parts: list[str] = []
    test_path: Optional[str] = None
    test_content: str = "No test file found"

    for path, content in code_context.items():
        if path == main_file_path:
            continue
        if ".test." in path or "test_" in path:
            test_path = path
            test_content = content
        else:
            related_parts.append(f"--- {path} ---\n{content}")

    related_block = "\n\n".join(related_parts) if related_parts else "No related files found"
    test_label = test_path or "unknown"

    prompt = f"""PRODUCTION ERROR:
  Type: {issue.error_type}
  Message: {issue.error_message}
  File: {issue.file_path}
  Function: {issue.function_name}
  Line: {issue.line_number}
  Occurrences: {issue.occurrence_count}

STACK TRACE:
{redacted_trace}

SOURCE FILE ({main_file_path}):
{main_content}

RELATED FILES:
{related_block}

TEST FILE ({test_label}):
{test_content}"""

    # Recurrence context
    if previous_pr_url:
        prompt += f"""

IMPORTANT: A previous fix was attempted (PR: {previous_pr_url}) but the same error has reoccurred.
The previous fix was insufficient. Please analyze why and propose a deeper fix."""

    prompt += "\n\nGenerate the fix following the rules and response format specified."
    return prompt


def _parse_response(raw: str) -> LLMFixResponse:
    """Parse the raw JSON string from GPT-4o into a validated model."""
    data = json.loads(raw)
    return LLMFixResponse(**data)


def generate_fix(
    issue: IssueRecord,
    code_context: dict[str, str],
    openai_api_key: str,
    previous_pr_url: Optional[str] = None,
) -> LLMFixResponse:
    """
    Call GPT-4o to generate a fix for the given issue.

    Raises:
        RuntimeError: If the LLM returns invalid JSON twice.
    """
    client = OpenAI(api_key=openai_api_key)
    user_prompt = _build_user_prompt(issue, code_context, previous_pr_url)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(2):
        logger.info("Calling GPT-4o (attempt %d)...", attempt + 1)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content or ""

        try:
            return _parse_response(raw_content)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("JSON parse failed (attempt %d): %s", attempt + 1, exc)
            if attempt == 0:
                # Retry with a follow-up message asking for valid JSON
                messages.append({"role": "assistant", "content": raw_content})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous response was not valid JSON. "
                        "Please return ONLY the valid JSON object matching "
                        "the specified response format. No extra text."
                    ),
                })

    raise RuntimeError(
        f"LLM returned invalid JSON after 2 attempts for issue {issue.id}"
    )
