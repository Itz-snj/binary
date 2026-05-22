import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import genai_client


def _clear_provider_keys(monkeypatch):
    for key in (
        "FREEMODEL_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
        "CEREBRAS_API_KEY",
        "TOGETHER_API_KEY",
        "MISTRAL_API_KEY",
        "GITHUB_MODELS_TOKEN",
        "HUGGINGFACE_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_configured_providers_skip_missing_keys(monkeypatch):
    _clear_provider_keys(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "freemodel,groq")

    assert genai_client.get_configured_providers() == []


def test_configured_providers_use_model_lists(monkeypatch):
    _clear_provider_keys(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "freemodel")
    monkeypatch.setenv("FREEMODEL_API_KEY", "fm-key")
    monkeypatch.setenv("FREEMODEL_MODELS", "FRE-test,FRE-second")

    providers = genai_client.get_configured_providers()

    assert [p.model_ref for p in providers] == ["freemodel:FRE-test", "freemodel:FRE-second"]


@pytest.mark.asyncio
async def test_generate_with_fallback_uses_next_provider(monkeypatch):
    _clear_provider_keys(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER_CHAIN", "freemodel,groq")
    monkeypatch.setenv("FREEMODEL_API_KEY", "fm-key")
    monkeypatch.setenv("FREEMODEL_MODEL", "FRE-test")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-test")

    calls = []

    async def fake_call(config, prompt, system_instruction, response_mime_type):
        calls.append(config.model_ref)
        if config.name == "freemodel":
            raise genai_client.ProviderUnavailable("rate limited")
        return "OK", config.model_ref

    monkeypatch.setattr(genai_client, "_call_openai_compatible", fake_call)

    text, model = await genai_client.generate_with_fallback("hello", max_retries=1)

    assert text == "OK"
    assert model == "groq:llama-test"
    assert calls == ["freemodel:FRE-test", "groq:llama-test"]


def test_json_response_mime_type_adds_instruction_not_response_format_by_default(monkeypatch):
    monkeypatch.delenv("LLM_SEND_RESPONSE_FORMAT", raising=False)
    config = genai_client.ProviderConfig(
        name="freemodel",
        base_url="https://freemodel.dev/v1",
        model="FRE-test",
        api_key_env="FREEMODEL_API_KEY",
        api_key="key",
    )

    payload = genai_client._payload(
        config,
        prompt="return json",
        system_instruction="system",
        response_mime_type="application/json",
    )

    assert "response_format" not in payload
    assert payload["messages"][0]["role"] == "system"
    assert "Return only one valid JSON object" in payload["messages"][0]["content"]


def test_extracts_chat_completion_content():
    data = {"choices": [{"message": {"content": "done"}}]}

    assert genai_client._extract_content(data) == "done"
