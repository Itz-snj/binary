"""
SlothOps Engine — Configuration
Loads environment variables and exposes typed settings.
Raises RuntimeError on missing required keys at startup.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Return env var value or raise if missing."""
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


# ── Required keys ────────────────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT: str | None = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# --- Optional LLM Providers ---
OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")
TOGETHER_API_KEY: str | None = os.getenv("TOGETHER_API_KEY")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

# --- Optional (sensible defaults) ---
SENTRY_WEBHOOK_SECRET: str | None = os.getenv("SENTRY_WEBHOOK_SECRET")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./slothops.db")
PORT: int = int(os.getenv("PORT", "8000"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
BASE_URL: str = os.getenv("BASE_URL", "")
GITHUB_WEBHOOK_SECRET: str | None = os.getenv("GITHUB_WEBHOOK_SECRET")
ROLLBACK_DEFAULT_MODE: str = os.getenv("ROLLBACK_DEFAULT_MODE", "approval_required")
ROLLBACK_DEFAULT_STRATEGY: str = os.getenv("ROLLBACK_DEFAULT_STRATEGY", "rollback_pr")
MAX_QA_LOG_CHARS: int = int(os.getenv("MAX_QA_LOG_CHARS", "4000"))
MAX_LLM_CONTEXT_CHARS: int = int(os.getenv("MAX_LLM_CONTEXT_CHARS", "24000"))
