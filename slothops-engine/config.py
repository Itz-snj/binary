"""
SlothOps Engine — Configuration
Loads environment variables and exposes typed settings.
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def utcnow() -> datetime:
    """Timezone-aware UTC now. Use this instead of datetime.utcnow() (deprecated)."""
    return datetime.now(timezone.utc)


# ── Optional LLM Providers ───────────────────────────────────────────────
LLM_PROVIDER_CHAIN: str = os.getenv(
    "LLM_PROVIDER_CHAIN",
    "freemodel,openrouter,groq,cerebras,together,mistral,github_models,huggingface",
)
FREEMODEL_API_KEY: str | None = os.getenv("FREEMODEL_API_KEY")
FREEMODEL_BASE_URL: str = os.getenv("FREEMODEL_BASE_URL", "https://freemodel.dev/v1")
FREEMODEL_MODEL: str = os.getenv("FREEMODEL_MODEL", "FRE-5.5")
OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
CEREBRAS_API_KEY: str | None = os.getenv("CEREBRAS_API_KEY")
CEREBRAS_BASE_URL: str = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
CEREBRAS_MODEL: str = os.getenv("CEREBRAS_MODEL", "llama3.1-8b")
TOGETHER_API_KEY: str | None = os.getenv("TOGETHER_API_KEY")
TOGETHER_BASE_URL: str = os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1")
TOGETHER_MODEL: str = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free")
MISTRAL_API_KEY: str | None = os.getenv("MISTRAL_API_KEY")
MISTRAL_BASE_URL: str = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
GITHUB_MODELS_TOKEN: str | None = os.getenv("GITHUB_MODELS_TOKEN")
GITHUB_MODELS_BASE_URL: str = os.getenv("GITHUB_MODELS_BASE_URL", "https://models.github.ai/inference")
GITHUB_MODELS_MODEL: str = os.getenv("GITHUB_MODELS_MODEL", "microsoft/phi-4")
HUGGINGFACE_API_KEY: str | None = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_BASE_URL: str = os.getenv("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1")
HUGGINGFACE_MODEL: str = os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct")

# ── Database ─────────────────────────────────────────────────────────────
# Primary async URL (asyncpg) for application queries
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://slothops:slothops_dev@localhost:5432/slothops",
)
# Direct sync URL (psycopg) for Alembic migrations
DIRECT_DATABASE_URL: str = os.getenv(
    "DIRECT_DATABASE_URL",
    "postgresql+psycopg://slothops:slothops_dev@localhost:5432/slothops",
)
# Legacy fallback — kept for test compatibility only
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./slothops.db")

# ── Server ───────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "8000"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
BASE_URL: str = os.getenv("BASE_URL", "")

# ── GitHub ───────────────────────────────────────────────────────────────
GITHUB_WEBHOOK_SECRET: str | None = os.getenv("GITHUB_WEBHOOK_SECRET")
SENTRY_WEBHOOK_SECRET: str | None = os.getenv("SENTRY_WEBHOOK_SECRET")

# ── Rollback Defaults ────────────────────────────────────────────────────
ROLLBACK_DEFAULT_MODE: str = os.getenv("ROLLBACK_DEFAULT_MODE", "approval_required")
ROLLBACK_DEFAULT_STRATEGY: str = os.getenv("ROLLBACK_DEFAULT_STRATEGY", "rollback_pr")

# ── QA ───────────────────────────────────────────────────────────────────
MAX_QA_LOG_CHARS: int = int(os.getenv("MAX_QA_LOG_CHARS", "4000"))
MAX_LLM_CONTEXT_CHARS: int = int(os.getenv("MAX_LLM_CONTEXT_CHARS", "24000"))
