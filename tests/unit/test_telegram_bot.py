"""Unit tests for the Telegram bridge logic (no network, no Telegram server)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from aether.bot.telegram import AetherTelegramBot


@pytest.mark.asyncio
async def test_answer_without_model_backend_is_graceful():
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager=None)
    out = await bot._answer("hello")
    assert "model backend is not running" in out


@pytest.mark.asyncio
async def test_answer_routes_through_cognitive_service(monkeypatch):
    async def fake_query(agent_id, query, model_manager):
        assert agent_id == "aria"
        assert query == "hello"
        assert model_manager == "mm"
        return "mock answer"

    monkeypatch.setattr("aether.cognitive.service.run_cognitive_query", fake_query)
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    assert await bot._answer("hello") == "mock answer"


@pytest.mark.asyncio
async def test_answer_falls_back_when_engine_raises(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("ollama down")

    monkeypatch.setattr("aether.cognitive.service.run_cognitive_query", boom)
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    out = await bot._answer("hello")
    assert "inference error" in out


@pytest.mark.asyncio
async def test_message_handler_replies(monkeypatch):
    reply = AsyncMock()
    update = SimpleNamespace(message=SimpleNamespace(text="hello", reply_text=reply))
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    monkeypatch.setattr(bot, "_answer", AsyncMock(return_value="engine answer"))
    await bot._on_message(update, None)
    reply.assert_awaited_once_with("engine answer")


@pytest.mark.asyncio
async def test_message_handler_skips_empty_text(monkeypatch):
    update = SimpleNamespace(message=SimpleNamespace(text="  ", reply_text=AsyncMock()))
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    monkeypatch.setattr(bot, "_answer", AsyncMock(return_value="ignored"))
    await bot._on_message(update, None)
    bot._answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_without_token_raises_cleanly(monkeypatch):
    """start() must surface telegram auth errors (no silent ignore)."""
    received = {}

    class FakeApp:
        def __init__(self):
            self.handlers = []
            self.updater = SimpleNamespace(
                start_polling=AsyncMock(return_value=None), stop=AsyncMock()
            )

        def add_handler(self, h):
            self.handlers.append(h)

        def builder(self):
            return self

        def token(self, t):
            received["token"] = t
            return self

        async def initialize(self):
            pass

        async def start(self):
            raise RuntimeError("Unauthorized: 401")

        async def stop(self):
            pass

        async def shutdown(self):
            pass

    monkeypatch.setattr(
        "aether.bot.telegram.AetherTelegramBot._build_application",
        lambda self: FakeApp(),
    )
    bot = AetherTelegramBot(token="bad-token", agent_id="aria", model_manager=None)
    with pytest.raises(RuntimeError, match="Unauthorized"):
        await bot.start()