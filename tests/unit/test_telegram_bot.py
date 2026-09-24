"""Unit tests for the Telegram bridge logic (no network, no Telegram server)."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from aether.bot.telegram import AetherTelegramBot, MAX_MESSAGE_CHARS


def mk_update(text="hello", user_id=42, chat_id=123):
    """Build a minimal fake Update namespace matching what the bot touches."""
    return SimpleNamespace(
        message=SimpleNamespace(text=text, reply_text=AsyncMock(return_value=SimpleNamespace(edit_text=AsyncMock()))),
        effective_chat=SimpleNamespace(id=chat_id),
        effective_user=SimpleNamespace(id=user_id),
    )


def mk_context():
    return SimpleNamespace(bot=SimpleNamespace(send_chat_action=AsyncMock()))


@pytest.mark.asyncio
async def test_answer_without_model_backend_is_graceful():
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager=None)
    out = await bot._answer("hello")
    assert "model backend is not running" in out


@pytest.mark.asyncio
async def test_answer_routes_through_cognitive_service(monkeypatch):
    async def fake_query(agent_id, query, model_manager, history=None):
        assert agent_id == "aria"
        assert query == "hello"
        assert model_manager == "mm"
        assert history is None
        return "mock answer"

    monkeypatch.setattr("aether.cognitive.service.run_cognitive_query", fake_query)
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    assert await bot._answer("hello") == "mock answer"


@pytest.mark.asyncio
async def test_answer_forwards_chat_history(monkeypatch):
    seen = {}

    async def fake_query(agent_id, query, model_manager, history=None):
        seen["history"] = history
        return "next answer"

    monkeypatch.setattr("aether.cognitive.service.run_cognitive_query", fake_query)
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    bot._history["123"] = [("user", "first"), ("assistant", "repl")]

    out = await bot._answer("next", "123")

    assert out == "next answer"
    assert seen["history"] == [("user", "first"), ("assistant", "repl")]
    assert list(bot._history["123"])[-2:] == [("user", "next"), ("assistant", "next answer")]


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
    update = mk_update(text="hello")
    context = mk_context()
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    monkeypatch.setattr(bot, "_answer", AsyncMock(return_value="engine answer"))
    await bot._on_message(update, context)
    update.message.reply_text.assert_awaited_once_with("engine answer", parse_mode="HTML")


@pytest.mark.asyncio
async def test_keep_typing_arms_chat_action():
    context = mk_context()
    bot = AetherTelegramBot(token="test", agent_id="aria")
    task = asyncio.create_task(bot._keep_typing(context.bot, "123"))
    await asyncio.sleep(0.1)
    task.cancel()
    await task
    context.bot.send_chat_action.assert_awaited()


@pytest.mark.asyncio
async def test_message_handler_skips_empty_text(monkeypatch):
    update = mk_update(text="  ")
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm")
    monkeypatch.setattr(bot, "_answer", AsyncMock(return_value="ignored"))
    await bot._on_message(update, None)
    bot._answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_allowlist_denies_unlisted(monkeypatch):
    update = mk_update(text="hello", user_id=999)
    context = mk_context()
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm", allowed_users={42})
    monkeypatch.setattr(bot, "_answer", AsyncMock(return_value="leak"))
    await bot._on_message(update, context)
    bot._answer.assert_not_awaited()
    update.message.reply_text.assert_awaited_once()
    assert "not on this bot's allowed-user list" in update.message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_allowlist_allows_listed(monkeypatch):
    update = mk_update(text="hi", user_id=42)
    bot = AetherTelegramBot(token="test", agent_id="aria", model_manager="mm", allowed_users={42})
    monkeypatch.setattr(bot, "_answer", AsyncMock(return_value="allowed"))
    await bot._on_message(update, mk_context())
    assert bot._answer.await_args.args[0] == "hi"


def test_parse_allowed_users():
    assert AetherTelegramBot._parse_allowed_users("1,2,3") == {1, 2, 3}
    assert AetherTelegramBot._parse_allowed_users(" 1 , 2 ") == {1, 2}
    assert AetherTelegramBot._parse_allowed_users("") is None
    assert AetherTelegramBot._parse_allowed_users("abc,,5") == {5}


def test_chunk_text_small_unchanged():
    bot = AetherTelegramBot(token="t", agent_id="a")
    assert bot._chunk_text("short") == ["short"]
    assert bot._chunk_text("   ") == ["(empty reply)"]


def test_chunk_text_splits_long():
    bot = AetherTelegramBot(token="t", agent_id="a")
    text = "\n".join(f"line {i} " + "x" * 100 for i in range(100))
    chunks = bot._chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 3500 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


@pytest.mark.asyncio
async def test_deliver_answer_chunks_with_markers():
    long = ("A" * 3400) + "\n" + ("B" * 3400)
    bot = AetherTelegramBot(token="t", agent_id="a")
    message = SimpleNamespace(reply_text=AsyncMock())
    await bot._deliver_answer(message, long)
    calls = [c.args[0] for c in message.reply_text.await_args_list]
    assert len(calls) == 2
    assert calls[0].startswith("(1/2) ")
    assert calls[1].startswith("(2/2) ")


@pytest.mark.asyncio
async def test_patience_message_edited_with_answer():
    bot = AetherTelegramBot(token="t", agent_id="a", patience_delay=0.0)
    holder = {}
    message = SimpleNamespace(reply_text=AsyncMock(return_value=SimpleNamespace(edit_text=AsyncMock())))
    await bot._patience(message, holder)
    assert holder["msg"] is not None
    assert "…" in message.reply_text.await_args.args[0]

    await bot._deliver_answer(message, "the real answer", holder)
    holder["msg"].edit_text.assert_awaited_once_with("the real answer", parse_mode="HTML")
    message.reply_text.assert_awaited_once()  # only the patience note, no duplicate final reply


@pytest.mark.asyncio
async def test_cmd_new_clears_history(monkeypatch):
    bot = AetherTelegramBot(token="t", agent_id="a")
    bot._history["555"] = [("user", "x"), ("assistant", "y")]
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=555), message=SimpleNamespace(reply_text=AsyncMock())
    )
    context = SimpleNamespace(_chat_id=555)
    await bot._cmd_new(update, context)
    assert "555" not in bot._history
    update.message.reply_text.assert_awaited_once_with(
        "🧹 Conversation history cleared. Fresh start!"
    )


@pytest.mark.asyncio
async def test_cmd_status_shows_provider_and_model():
    bot = AetherTelegramBot(token="t", agent_id="dracko", model_manager="mm")
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=1), message=SimpleNamespace(reply_text=AsyncMock())
    )
    await bot._cmd_status(update, None)
    text = update.message.reply_text.await_args.args[0]
    assert "dracko" in text
    assert "Engine: <b>running</b>" in text


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