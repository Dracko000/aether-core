"""Unit tests for the model-provider registry and remote adapters (no network)."""
import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel

from aether.model.anthropic_adapter import AnthropicAdapter
from aether.model.openai_compat import OpenAICompatAdapter
from aether.model.providers import (
    PROVIDERS,
    fetch_provider_models,
    get_provider,
    provider_options,
)


# --------------------------------------------------------------- registry

def test_registry_has_local_and_remote_providers():
    assert "ollama" in PROVIDERS
    for pid in ("openai", "openrouter", "groq", "deepseek", "xai", "gemini", "anthropic"):
        assert pid in PROVIDERS, pid


def test_provider_options_public_and_sorted():
    opts = provider_options()
    ids = [o["id"] for o in opts]
    assert ids[0] == "ollama"  # local first
    by_id = {o["id"]: o for o in opts}
    assert by_id["openai"]["needs_key"] is True
    assert by_id["ollama"]["needs_key"] is False
    assert by_id["openai"]["key_configured"] is False  # no keys in test env
    # never leak keys
    assert all("api_key" not in o for o in opts)
    assert all(o["kind"] in ("ollama", "openai", "anthropic") for o in opts)


def test_get_provider_unknown_returns_none():
    assert get_provider("not-a-provider") is None
    assert get_provider("") is None
    assert get_provider("OPENAI") is not None  # ids are lower-cased


# ---------------------------------------------------------- catalogue fetch

def test_fetch_provider_models_ollama(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "llama3.2:1b"}, {"name": "qwen2.5:0.5b"}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    models = asyncio.run(fetch_provider_models("ollama", base_url="http://ollama:11434"))
    assert models == ["llama3.2:1b", "qwen2.5:0.5b"]


def test_fetch_provider_models_openai_sends_auth(monkeypatch):
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    models = asyncio.run(fetch_provider_models("openai", api_key="sk-test"))
    assert models == ["gpt-4o-mini", "gpt-4o"]
    assert seen["auth"] == "Bearer sk-test"


def test_fetch_provider_models_failure_returns_empty(monkeypatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    assert asyncio.run(fetch_provider_models("openai", api_key="sk-x")) == []


# ------------------------------------------------------- OpenAI-compatible

class Weather(BaseModel):
    city: str
    temp_c: float


@pytest.mark.asyncio
async def test_openai_compat_chat_and_structured():
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("response_format"):
            return httpx.Response(
                200, json={"choices": [{"message": {"content": '{"city":"Jakarta","temp_c":31.5}'}}]}
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "hello from gpt"}}]},
        )

    adapter = OpenAICompatAdapter(
        base_url="https://api.openai.com/v1",
        model_name="gpt-4o-mini",
        api_key="sk-test",
    )
    import aether.model.openai_compat as mod

    original = httpx.AsyncClient
    mod.httpx.AsyncClient = lambda **kw: original(
        transport=httpx.MockTransport(handler), **kw
    )
    try:
        out = await adapter.chat([{"role": "user", "content": "hi"}])
        assert out == "hello from gpt"
        w = await adapter.structured([{"role": "user", "content": "report"}], Weather)
        assert w.city == "Jakarta"
        assert w.temp_c == 31.5
        gen = await adapter.generate("prompt")
        assert gen == "hello from gpt"
    finally:
        mod.httpx.AsyncClient = original


@pytest.mark.asyncio
async def test_openai_compat_strict_json_extraction():
    adapter = OpenAICompatAdapter(base_url="http://x/v1", model_name="m", api_key="k")
    assert adapter._extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert adapter._extract_json('prefix {"a": 1} suffix') == '{"a": 1}'


# ------------------------------------------------------------- Anthropic

@pytest.mark.asyncio
async def test_anthropic_chat_maps_system_and_parses():
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["x-api-key"] == "sk-ant"
        assert "system" in body
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "sure thing"}]},
        )

    import aether.model.anthropic_adapter as mod

    original = httpx.AsyncClient
    mod.httpx.AsyncClient = lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    try:
        adapter = AnthropicAdapter(api_key="sk-ant", model_name="claude-sonnet-4-5")
        out = await adapter.chat(
            [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]
        )
        assert out == "sure thing"
    finally:
        mod.httpx.AsyncClient = original


@pytest.mark.asyncio
async def test_anthropic_structured_parses_fenced_json():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": '```json\n{"city":"Tokyo","temp_c":18.0}\n```'}]},
        )

    import aether.model.anthropic_adapter as mod

    original = httpx.AsyncClient
    mod.httpx.AsyncClient = lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    try:
        adapter = AnthropicAdapter(api_key="sk-ant", model_name="claude-haiku-4-5")
        w = await adapter.structured([{"role": "user", "content": "weather"}], Weather)
        assert w.city == "Tokyo"
        assert w.temp_c == 18.0
    finally:
        mod.httpx.AsyncClient = original