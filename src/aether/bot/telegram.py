"""Telegram bridge: forwards chat messages to one fixed Aether agent and replies.

Interaction model adapted from the Hermes Agent gateway
(``plugins/platforms/telegram`` + ``gateway/assets/status_phrases.yaml``):

* typing indicator while the engine works, re-armed every few seconds
* a low-key *patience message* ("still working on it…") when a reply takes
  long — edited in place with the real answer when it lands
* answers chunked below the 4096-byte Telegram limit with ``(N/M)`` markers
* HTML-safe formatting, slash commands (``/start`` ``/help`` ``/status``
  ``/model`` ``/new`` ``/about``), per-user/chat allowlisting and per-chat
  multi-turn history.

The bot runs as a long-polling background task inside the API server. All
chats are mapped to ``settings.TELEGRAM_AGENT_ID`` through the shared
cognitive service, so every message is answered by the configured model
backend (local Ollama or a remote provider).

The heavy ``python-telegram-bot`` import is lazy so importing the API app
does not require the Telegram stack at import time.
"""
import asyncio
import logging
import random
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from aether.config import settings

logger = logging.getLogger("aether.bot.telegram")

# Casual patience phrases (adapted from hermes gateway/assets/status_phrases.yaml).
STATUS_PHRASES: tuple = (
    "still working on it",
    "this is taking a bit, still running",
    "still checking, no panic",
    "one sec, this is still going",
    "still making progress",
    "waiting for the result",
    "still here, checking",
    "this one needs a minute",
    "still going, not frozen",
    "still chewing through it",
    "working through the slow step",
    "still in progress",
)

MAX_MESSAGE_CHARS = 4096
# Leave headroom for the (N/M) marker + HTML entity expansion (escaping can
# inflate a chunk by several percent); 3500 keeps a published message well
# under Telegram's 4096-byte cap even for entity-heavy answers.
CHUNK_LIMIT = 3500
HISTORY_TURNS = 8
TYPING_INTERVAL = 4.0
PATIENCE_DELAY = 6.0


class AetherTelegramBot:
    """Long-polling Telegram bot bridging chats to a fixed Aether agent."""

    def __init__(
        self,
        token: str,
        agent_id: str,
        model_manager=None,
        allowed_users: Optional[Set[int]] = None,
        allow_all: Optional[bool] = None,
        patience_delay: float = PATIENCE_DELAY,
    ):
        self.token = token
        self.agent_id = agent_id
        self.model_manager = model_manager
        self.patience_delay = patience_delay
        self.application: Optional[object] = None
        self.allowed_users = (
            allowed_users
            if allowed_users is not None
            else self._parse_allowed_users(settings.TELEGRAM_ALLOWED_USERS)
        )
        self.allow_all = (
            allow_all
            if allow_all is not None
            else bool(settings.TELEGRAM_ALLOW_ALL_USERS)
        )
        # chat_id -> deque[(role, text)] recent turns (multi-turn continuity)
        self._history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=HISTORY_TURNS * 2)
        )

    @staticmethod
    def _parse_allowed_users(raw: str) -> Optional[Set[int]]:
        raw = (raw or "").strip()
        if not raw:
            return None
        ids: Set[int] = set()
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids or None

    @staticmethod
    def _import_telegram():
        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )

        return Update, Application, CommandHandler, MessageHandler, filters

    def _build_application(self):
        Update, Application, CommandHandler, MessageHandler, filters = self._import_telegram()
        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("help", self._cmd_help))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("model", self._cmd_model))
        app.add_handler(CommandHandler("new", self._cmd_new))
        app.add_handler(CommandHandler("about", self._cmd_about))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        return app

    async def start(self) -> None:
        """Start long polling. Raises if the token is rejected by Telegram."""
        Update, _, _, _, _ = self._import_telegram()
        self.application = self._build_application()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info(
            "Telegram bot started (polling) -> agent %s, provider %s, model %s",
            self.agent_id,
            settings.MODEL_PROVIDER,
            self._effective_model(),
        )

    async def stop(self) -> None:
        if self.application is None:
            return
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        self.application = None
        logger.info("Telegram bot stopped")

    async def send_message(self, chat_id: str, text: str) -> None:
        """Send a proactive message to a chat via the running bot."""
        if self.application is None:
            raise RuntimeError("bot not started")
        await self.application.bot.send_message(chat_id=chat_id, text=text)

    # ------------------------------------------------------------- helpers

    @staticmethod
    def _provider_label() -> str:
        from aether.model.providers import get_provider

        provider = get_provider(settings.MODEL_PROVIDER)
        return provider.display_name if provider else settings.MODEL_PROVIDER

    @staticmethod
    def _effective_model() -> str:
        from aether.model.factory import effective_model_name

        return effective_model_name()

    def _is_allowed(self, update) -> bool:
        if self.allow_all or self.allowed_users is None:
            return True
        user = getattr(update, "effective_user", None) or getattr(
            getattr(update, "message", None), "from_user", None
        )
        uid = getattr(user, "id", None)
        return uid is not None and uid in self.allowed_users

    @classmethod
    def _escape_html(cls, text: str) -> str:
        return (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    @classmethod
    def _chunk_text(cls, text: str, limit: int = CHUNK_LIMIT) -> List[str]:
        """Split ``text`` into chat-safe chunks (prefers paragraph breaks)."""
        text = (text or "").strip()
        if not text:
            return ["(empty reply)"]
        if len(text) <= limit:
            return [text]
        chunks: List[str] = []
        buf = ""
        for para in text.split("\n"):
            if buf and len(buf) + 1 + len(para) > limit:
                chunks.append(buf)
                buf = ""
            if len(para) > limit:
                if buf:
                    chunks.append(buf)
                    buf = ""
                for i in range(0, len(para), limit):
                    chunks.append(para[i : i + limit])
                continue
            buf = f"{buf}\n{para}" if buf else para
        if buf:
            chunks.append(buf)
        return chunks

    # ----------------------------------------------------------- messaging

    async def _keep_typing(self, bot, chat_id: str) -> None:
        try:
            while True:
                await bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(TYPING_INTERVAL)
        except asyncio.CancelledError:
            pass
        except Exception:  # pragma: no cover - transient network/timer
            pass

    async def _patience(self, message, holder: dict) -> None:
        """Send a casual 'still working' note after a delay (edited away later)."""
        try:
            await asyncio.sleep(self.patience_delay)
            if holder.get("done"):
                return
            phrase = random.choice(STATUS_PHRASES)
            holder["msg"] = await message.reply_text(f"… {phrase}")
        except asyncio.CancelledError:
            pass
        except Exception:  # pragma: no cover - defensively keep the loop alive
            pass

    async def _deliver_answer(
        self, message, answer: str, holder: Optional[dict] = None
    ) -> None:
        """Send the answer, chunked; reuses the patience message if present."""
        holder = holder or {}
        parts = self._chunk_text(answer)
        total = len(parts)
        first = parts[0]

        def marker(i: int) -> str:
            return f"({i}/{total}) " if total > 1 else ""

        status = holder.get("msg")
        if status is not None:
            try:
                await status.edit_text(
                    marker(1) + self._escape_html(first), parse_mode="HTML"
                )
            except Exception:  # pragma: no cover - message may be gone
                status = None
        if status is None:
            await message.reply_text(
                marker(1) + self._escape_html(first), parse_mode="HTML"
            )
        for i, part in enumerate(parts[1:], start=2):
            await message.reply_text(
                marker(i) + self._escape_html(part), parse_mode="HTML"
            )

    async def _answer(self, text: str, chat_id: Optional[str] = None) -> str:
        """Route one message through the engine; never raises (bot keeps running)."""
        if self.model_manager is None:
            return "Aether model backend is not running. Check the /setup page."
        try:
            from aether.cognitive.service import run_cognitive_query

            history = list(self._history.get(chat_id, ())) if chat_id else None
            answer = await run_cognitive_query(
                self.agent_id, text, self.model_manager, history=history
            )
            answer = answer or "(agent returned no answer)"
            if chat_id is not None:
                turns = self._history[chat_id]
                turns.append(("user", text))
                turns.append(("assistant", answer))
            return answer
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Engine call failed in Telegram bridge")
            return f"(inference error: {exc})"

    # -------------------------------------------------------------- commands

    async def _cmd_start(self, update, context):
        await update.message.reply_text(
            f"👋 Hi! I'm connected to Aether agent <b>'{self.agent_id}'</b>.\n"
            f"Model: <b>{self._provider_label()}</b> · {self._effective_model()}\n\n"
            "Send me any message — I route it through the engine and answer.\n"
            "Commands: /help · /status · /model · /new · /about",
            parse_mode="HTML",
        )

    async def _cmd_help(self, update, context):
        await update.message.reply_text(
            "🧭 <b>How to talk to me</b>\n"
            "Just send a message. I remember the last few turns of this chat, "
            "pull agent memory, and reply with the model's answer.\n\n"
            "<b>Commands</b>\n"
            "/status — backend health\n"
            "/model — active provider + model\n"
            "/new — clear this chat's conversation history\n"
            "/about — what this is",
            parse_mode="HTML",
        )

    async def _cmd_status(self, update, context):
        chat_id = str(update.effective_chat.id)
        history = self._history.get(chat_id)
        turns = len(history) // 2 if history else 0
        access = (
            "everyone"
            if self.allow_all or self.allowed_users is None
            else f"allowlist ({len(self.allowed_users)} users)"
        )
        await update.message.reply_text(
            "🩺 <b>Status</b>\n"
            f"• Agent: <b>{self.agent_id}</b>\n"
            f"• Provider: <b>{self._provider_label()}</b>\n"
            f"• Model: <b>{self._effective_model()}</b>\n"
            f"• Engine: <b>{'running' if self.model_manager is not None else 'offline'}</b>\n"
            f"• Memory: <b>{turns} exchange(s)</b> in this chat\n"
            f"• Access: {access}",
            parse_mode="HTML",
        )

    async def _cmd_model(self, update, context):
        await update.message.reply_text(
            f"🤖 <b>{self._provider_label()}</b>\n{self._effective_model()}\n\n"
            "Change it anytime on the console → Setup tab.",
            parse_mode="HTML",
        )

    async def _cmd_new(self, update, context):
        chat_id = str(update.effective_chat.id)
        if chat_id in self._history:
            del self._history[chat_id]
        await update.message.reply_text("🧹 Conversation history cleared. Fresh start!")

    async def _cmd_about(self, update, context):
        await update.message.reply_text(
            "⚡ <b>Aether Core</b> — local-first autonomous agent runtime.\n"
            "One fixed agent answers every chat through the cognitive engine "
            "(memory retrieval + drive-based reasoning), backed by a local model "
            "(Ollama) or a remote provider (OpenAI, Anthropic, OpenRouter, …).\n\n"
            "Console: the /setup page on your VPS.",
            parse_mode="HTML",
        )

    # -------------------------------------------------------------- ingress

    async def _on_message(self, update, context):
        message = update.message
        text = (message.text or "").strip()
        if not text:
            return
        if not self._is_allowed(update):
            await message.reply_text(
                "⛔ Sorry, you're not on this bot's allowed-user list."
            )
            return
        chat_id = str(update.effective_chat.id)
        typing_task = asyncio.create_task(self._keep_typing(context.bot, chat_id))
        holder: dict = {}
        patience_task = asyncio.create_task(self._patience(message, holder))
        try:
            answer = await self._answer(text, chat_id)
            holder["done"] = True
            await self._deliver_answer(message, answer, holder)
        finally:
            typing_task.cancel()
            patience_task.cancel()