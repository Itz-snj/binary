"""PR summary and developer recommendation generation."""

from __future__ import annotations

import json
import logging

from app.llm.client import generate_with_fallback

logger = logging.getLogger("slothops.pr_insights")

PROMPT = """You are SlothOps reviewing a Pull Request.

Return concise markdown with these sections:
## SlothOps PR Insights
### What changed
### Risk summary
### Suggested improvements
### Developer preferences

Codebase context:
{codebase_context}

Developer preferences:
{developer_config}

Changed files:
{changed_files}
"""


async def generate_pr_insights(
    changed_files: list[dict],
    codebase_context: str = "",
    developer_config: dict | None = None,
) -> str:
    if not changed_files:
        return ""
    files_block = ""
    for f in changed_files:
        files_block += f"\n--- {f.get('path')} ---\n{f.get('content', '')[:8000]}\n"
    prompt = PROMPT.format(
        codebase_context=codebase_context or "(No repository context provided)",
        developer_config=json.dumps(developer_config or {}, indent=2),
        changed_files=files_block,
    )
    try:
        text, _ = await generate_with_fallback(prompt=prompt)
        return text
    except Exception as exc:
        logger.error("PR insights generation failed: %s", exc)
        return ""
