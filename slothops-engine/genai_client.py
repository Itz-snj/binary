"""
SlothOps Engine — Centralized GenAI Client (Multi-Provider)
Provides fallback support between Vertex AI, Anthropic (Claude), OpenRouter,
and other providers.
"""

from __future__ import annotations

import os
import logging
import asyncio
import random
import httpx

from google import genai

logger = logging.getLogger("slothops.genai_client")

PROVIDER_CHAIN = [
    {"provider": "vertex", "model": "gemini-2.5-pro"},
    {"provider": "openrouter", "model": "deepseek/deepseek-v3.2"},
    {"provider": "openrouter", "model": "qwen/qwen-2.5-coder-32b"},
    {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    {"provider": "vertex", "model": "gemini-2.5-flash"},
    {"provider": "anthropic", "model": "claude-haiku-4-20250514"},
]

# Cached client instance (singleton per process)
_client: genai.Client | None = None
_openrouter_client: httpx.AsyncClient | None = None
_anthropic_client = None  # anthropic.AsyncAnthropic | None


def get_client() -> genai.Client:
    """
    Return a google-genai Client configured for Vertex AI.

    Reads from environment variables:
      - GOOGLE_APPLICATION_CREDENTIALS (optional) — Path to service account JSON
      - GOOGLE_CLOUD_PROJECT  (optional) — GCP project ID
      - GOOGLE_CLOUD_LOCATION (default: us-central1)

    The GOOGLE_APPLICATION_CREDENTIALS env var is automatically picked up by
    the Google Auth library to authenticate API calls.
    """
    global _client
    if _client is not None:
        return _client

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    if not project:
        logger.warning("GOOGLE_CLOUD_PROJECT not set — Vertex AI provider unavailable. Falling back to other providers.")
        return None

    if creds_path and not os.path.exists(creds_path):
        logger.warning(
            "GOOGLE_APPLICATION_CREDENTIALS points to %s but file not found. "
            "Falling back to Application Default Credentials.",
            creds_path,
        )

    logger.info(
        "Initializing Vertex AI genai client (project=%s, location=%s, creds=%s)",
        project,
        location,
        creds_path or "ADC",
    )

    _client = genai.Client(
        vertexai=True,
        project=project,
        location=location,
    )
    return _client


async def _get_openrouter_client() -> httpx.AsyncClient:
    """Return async HTTP client for OpenRouter API."""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
    return _openrouter_client


async def _call_openrouter(prompt: str, model: str, system_instruction: str | None = None) -> tuple[str, str]:
    """Call OpenRouter API with specified model."""
    client = await _get_openrouter_client()
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter provider")

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 8192,
    }

    try:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content, model
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise Exception("RateLimitError")
        raise


async def _get_anthropic_client():
    """Return async Anthropic client (lazy-initialized singleton)."""
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic provider")
        _anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
    return _anthropic_client


async def _call_anthropic(prompt: str, model: str, system_instruction: str | None = None) -> tuple[str, str]:
    """Call Anthropic (Claude) API with specified model."""
    client = await _get_anthropic_client()

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": model,
        "max_tokens": 8192,
        "messages": messages,
    }
    if system_instruction:
        kwargs["system"] = system_instruction

    try:
        resp = await client.messages.create(**kwargs)
        content = resp.content[0].text if resp.content else ""
        return content, model
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate" in err_str.lower() or "overloaded" in err_str.lower():
            raise Exception("RateLimitError")
        raise


async def _call_vertex(prompt: str, model: str, system_instruction: str | None = None) -> tuple[str, str]:
    """Call Vertex AI API with specified model."""
    import asyncio

    client = get_client()

    config = None
    if system_instruction:
        from google.genai import types as genai_types
        config = genai_types.GenerateContentConfig(system_instruction=system_instruction)

    try:
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=prompt,
            config=config
        )
        return (resp.text or ""), model
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise Exception("RateLimitError")
        raise

_llm_lock = asyncio.Lock()

async def generate_with_fallback(
    prompt: str,
    preferred_model: str = "gemini-2.5-pro",
    fallback_model: str = "gemini-2.5-flash",
    max_retries: int = 2,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
) -> tuple[str, str]:
    """Returns (response_text, model_used). Tries all providers in chain with fallback."""
    async with _llm_lock:
        for provider_config in PROVIDER_CHAIN:
            provider = provider_config["provider"]
            model = provider_config["model"]

            for attempt in range(max_retries):
                try:
                    logger.info("🤖 Calling LLM with provider=%s model=%s...", provider, model)

                    if provider == "vertex":
                        result, used_model = await _call_vertex(prompt, model, system_instruction)
                    elif provider == "openrouter":
                        result, used_model = await _call_openrouter(prompt, model, system_instruction)
                    elif provider == "anthropic":
                        result, used_model = await _call_anthropic(prompt, model, system_instruction)
                    else:
                        logger.warning("Unknown provider %s, skipping", provider)
                        continue

                    return result, used_model

                except Exception as e:
                    if "RateLimitError" in str(e) or "429" in str(e):
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning("⚠️ Rate limited on %s/%s, waiting %.1fs...", provider, model, delay)
                        await asyncio.sleep(delay)
                    elif "400" in str(e):
                        logger.error("❌ 400 Bad Request error from %s/%s: %s", provider, model, e)
                        continue
                    else:
                        logger.warning("❌ Error from %s/%s: %s", provider, model, e)
                        continue

        raise RuntimeError("All LLM providers exhausted and rate limited after retries")
