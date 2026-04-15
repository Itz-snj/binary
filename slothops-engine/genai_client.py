"""
SlothOps Engine — Centralized GenAI Client (Vertex AI)
Provides a single factory function for creating the google-genai client
configured to use Vertex AI with a service account credentials file.
"""

from __future__ import annotations

import os
import logging

from google import genai

logger = logging.getLogger("slothops.genai_client")

# Cached client instance (singleton per process)
_client: genai.Client | None = None


def get_client() -> genai.Client:
    """
    Return a google-genai Client configured for Vertex AI.

    Reads from environment variables:
      - GOOGLE_APPLICATION_CREDENTIALS (required) — Path to service account JSON
      - GOOGLE_CLOUD_PROJECT  (required) — GCP project ID
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
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT environment variable is required for Vertex AI. "
            "Set it to your GCP project ID."
        )

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


import asyncio
import random

_llm_lock = asyncio.Lock()

async def generate_with_fallback(
    prompt: str,
    preferred_model: str = "gemini-2.5-pro",
    fallback_model: str = "gemini-2.5-flash",
    max_retries: int = 2,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
) -> tuple[str, str]:
    """Returns (response_text, model_used). Serialized via lock to prevent RPM spikes."""
    async with _llm_lock:
        client = get_client()
        for model in (preferred_model, fallback_model):
            for attempt in range(max_retries):
                try:
                    logger.info("🤖 Calling LLM with model %s...", model)
                    
                    config = None
                    if system_instruction or response_mime_type:
                        from google.genai import types as genai_types
                        kwargs = {}
                        if system_instruction:
                            kwargs["system_instruction"] = system_instruction
                        if response_mime_type:
                            kwargs["response_mime_type"] = response_mime_type
                        config = genai_types.GenerateContentConfig(**kwargs)
                        
                    resp = client.models.generate_content(
                        model=model, 
                        contents=prompt,
                        config=config
                    )
                    return (resp.text or ""), model
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        delay = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning("⚠️ Rate limited on %s, waiting %.1fs...", model, delay)
                        await asyncio.sleep(delay)
                    elif "400" in str(e):
                        logger.error("❌ 400 Bad Request error from %s: %s", model, e)
                        raise
                    else:
                        logger.error("❌ Unexpected error from %s: %s", model, e)
                        raise
        raise RuntimeError("All LLM models exhausted and rate limited after retries")
