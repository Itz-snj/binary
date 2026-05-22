"""
SlothOps Engine - centralized LLM client.

All product code should call generate_with_fallback() instead of importing a
provider SDK directly. Providers here are OpenAI-compatible HTTP APIs so SlothOps
can swap free/low-cost inference backends without touching the pipeline code.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("slothops.genai_client")

DEFAULT_PROVIDER_CHAIN = (
    "freemodel,"
    "openrouter,"
    "groq,"
    "cerebras,"
    "together,"
    "mistral,"
    "github_models,"
    "huggingface"
)

DEFAULT_MODELS = {
    "freemodel": "FRE-5.5,FRE-5.4",
    "openrouter": "openrouter/free",
    "groq": "llama-3.1-8b-instant",
    "cerebras": "llama3.1-8b",
    "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "mistral": "mistral-small-latest",
    "github_models": "microsoft/phi-4",
    "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct",
}

DEFAULT_BASE_URLS = {
    "freemodel": "https://freemodel.dev/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "together": "https://api.together.xyz/v1",
    "mistral": "https://api.mistral.ai/v1",
    "github_models": "https://models.github.ai/inference",
    "huggingface": "https://router.huggingface.co/v1",
}

API_KEY_ENV = {
    "freemodel": "FREEMODEL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "together": "TOGETHER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "github_models": "GITHUB_MODELS_TOKEN",
    "huggingface": "HUGGINGFACE_API_KEY",
}

PROVIDER_DISPLAY = {
    "freemodel": "FreeModel",
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "cerebras": "Cerebras",
    "together": "Together AI",
    "mistral": "Mistral AI",
    "github_models": "GitHub Models",
    "huggingface": "Hugging Face Router",
}


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key_env: str
    api_key: str

    @property
    def display_name(self) -> str:
        return PROVIDER_DISPLAY.get(self.name, self.name)

    @property
    def chat_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    @property
    def model_ref(self) -> str:
        return f"{self.name}:{self.model}"


class ProviderUnavailable(RuntimeError):
    """Raised when a configured provider cannot be called in this process."""


_llm_lock = asyncio.Lock()


def _csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _env_name(provider: str, suffix: str) -> str:
    return f"{provider.upper()}_{suffix}"


def _models_for_provider(provider: str) -> list[str]:
    configured = os.getenv(_env_name(provider, "MODELS")) or os.getenv(_env_name(provider, "MODEL"))
    return _csv(configured or DEFAULT_MODELS.get(provider, ""))


def _provider_config(provider: str, model: str) -> ProviderConfig:
    key_env = API_KEY_ENV.get(provider, _env_name(provider, "API_KEY"))
    return ProviderConfig(
        name=provider,
        base_url=os.getenv(_env_name(provider, "BASE_URL"), DEFAULT_BASE_URLS.get(provider, "")),
        model=model,
        api_key_env=key_env,
        api_key=os.getenv(key_env, ""),
    )


def get_configured_providers() -> list[ProviderConfig]:
    """
    Return provider/model entries in execution order.

    Missing API keys are filtered out so local dev can keep a large default chain
    and only enable the services that have credentials.
    """
    chain = _csv(os.getenv("LLM_PROVIDER_CHAIN", DEFAULT_PROVIDER_CHAIN))
    providers: list[ProviderConfig] = []

    for provider in chain:
        for model in _models_for_provider(provider):
            config = _provider_config(provider, model)
            if not config.base_url:
                logger.debug("Skipping LLM provider %s because no base URL is configured", provider)
                continue
            if not config.api_key:
                logger.debug("Skipping LLM provider %s/%s because %s is not set", provider, model, config.api_key_env)
                continue
            providers.append(config)

    return providers


def _headers(config: ProviderConfig) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    if config.name == "openrouter":
        base_url = os.getenv("BASE_URL") or "https://slothops.local"
        headers["HTTP-Referer"] = base_url
        headers["X-Title"] = os.getenv("SLOTHOPS_APP_NAME", "SlothOps")

    return headers


def _messages(prompt: str, system_instruction: str | None, response_mime_type: str | None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    system_parts: list[str] = []

    if system_instruction:
        system_parts.append(system_instruction)
    if response_mime_type == "application/json":
        system_parts.append("Return only one valid JSON object. Do not wrap it in markdown.")

    if system_parts:
        messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    messages.append({"role": "user", "content": prompt})
    return messages


def _payload(
    config: ProviderConfig,
    prompt: str,
    system_instruction: str | None,
    response_mime_type: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": _messages(prompt, system_instruction, response_mime_type),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "8192")),
    }

    # Some OpenAI-compatible providers reject response_format. Keep it opt-in
    # while still improving JSON reliability through the system instruction.
    if (
        response_mime_type == "application/json"
        and os.getenv("LLM_SEND_RESPONSE_FORMAT", "false").lower() == "true"
    ):
        payload["response_format"] = {"type": "json_object"}

    return payload


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM provider returned no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)

    text = choices[0].get("text")
    if isinstance(text, str):
        return text

    raise RuntimeError("LLM provider response did not include message content")


def _retryable_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


async def _call_openai_compatible(
    config: ProviderConfig,
    prompt: str,
    system_instruction: str | None,
    response_mime_type: str | None,
) -> tuple[str, str]:
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            config.chat_url,
            headers=_headers(config),
            json=_payload(config, prompt, system_instruction, response_mime_type),
        )

    if _retryable_status(response.status_code):
        raise ProviderUnavailable(f"retryable_status:{response.status_code}")

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = response.text[:500]
        raise RuntimeError(f"{config.model_ref} returned HTTP {response.status_code}: {body}") from exc

    return _extract_content(response.json()), config.model_ref


def _ordered_providers(preferred_model: str | None, fallback_model: str | None) -> list[ProviderConfig]:
    providers = get_configured_providers()
    hints = [model for model in (preferred_model, fallback_model) if model]
    if not hints:
        return providers

    hinted: list[ProviderConfig] = []
    remaining: list[ProviderConfig] = []
    for config in providers:
        if config.model in hints or config.model_ref in hints:
            hinted.append(config)
        else:
            remaining.append(config)
    return hinted + remaining


async def generate_with_fallback(
    prompt: str,
    preferred_model: str | None = None,
    fallback_model: str | None = None,
    max_retries: int = 2,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
) -> tuple[str, str]:
    """
    Return (response_text, provider:model).

    preferred_model and fallback_model are kept for caller compatibility. They
    can now reference either a raw model name or "provider:model"; if omitted or
    unavailable, the env-configured provider chain is used.
    """
    providers = _ordered_providers(preferred_model, fallback_model)
    if not providers:
        raise RuntimeError(
            "No LLM providers are configured. Set at least one API key such as "
            "FREEMODEL_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY, "
            "TOGETHER_API_KEY, MISTRAL_API_KEY, GITHUB_MODELS_TOKEN, or HUGGINGFACE_API_KEY."
        )

    errors: list[str] = []
    async with _llm_lock:
        for config in providers:
            for attempt in range(max(max_retries, 1)):
                try:
                    logger.info("Calling LLM provider=%s model=%s", config.display_name, config.model)
                    return await _call_openai_compatible(
                        config=config,
                        prompt=prompt,
                        system_instruction=system_instruction,
                        response_mime_type=response_mime_type,
                    )
                except (ProviderUnavailable, httpx.TimeoutException, httpx.ConnectError) as exc:
                    errors.append(f"{config.model_ref}: {exc}")
                    delay = (2**attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Retryable LLM error from %s/%s on attempt %d: %s",
                        config.name,
                        config.model,
                        attempt + 1,
                        exc,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                except Exception as exc:
                    errors.append(f"{config.model_ref}: {exc}")
                    logger.warning("LLM provider %s/%s failed: %s", config.name, config.model, exc)
                    break

    raise RuntimeError("All configured LLM providers failed: " + " | ".join(errors[-5:]))


async def health_check() -> dict[str, Any]:
    """Small live check used by /api/health/llm."""
    import time

    start = time.time()
    response, model_ref = await generate_with_fallback(
        prompt="Reply with exactly: OK",
        max_retries=1,
    )
    latency_ms = int((time.time() - start) * 1000)
    provider, _, model = model_ref.partition(":")

    return {
        "status": "healthy",
        "provider": PROVIDER_DISPLAY.get(provider, provider),
        "model": model or model_ref,
        "model_ref": model_ref,
        "latency_ms": latency_ms,
        "response": response.strip()[:50],
        "configured_providers": [config.model_ref for config in get_configured_providers()],
    }
