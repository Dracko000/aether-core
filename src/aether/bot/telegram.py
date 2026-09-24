"""Telegram bridge: forwards chat messages to one fixed Aether agent and replies.

The bot runs as a long-polling background task inside the API server. All
chats are mapped to ``settings.TELEGRAM_AGENT_ID`` through the shared
cognitive service, so every message is answered by the model backend
(Ollama) with agent memory retrieval.

The heavy ``python-telegram-bot`` import is lazy so importing the API app
does not require the Telegram stack at import time.
"""
import logging
from typing import Optional

logger = logging.getLogger("aether.bot.telegram")


class AetherTelegramBot:
    """Long-polling Telegram bot bridging chats to a fixed Aether agent."""

    def __init__(self, token: str, agent_id: str, model_manager=None):
        self.token = token
        self.agent_id = agent_id
        self.model_manager = model_manager
        self.application: Optional[object] = None

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
        logger.info("Telegram bot started (polling) -> agent %s", self.agent_id)

    async def stop(self) -> None:
        if self.application is None:
            return
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        self.application = None
        logger.info("Telegram bot stopped")

    async def _cmd_start(self, update, context):
        await update.message.reply_text(
            f"Hi! I'm connected to Aether agent '{self.agent_id}'.\n"
            "Send me any message and I'll route it through the engine and reply with the answer."
        )

    async def _cmd_help(self, update, context):
        await update.message.reply_text(
            "Just send a message — I forward it to the Aether agent and reply with its answer."
        )

    async def _on_message(self, update, context):
        text = (update.message.text or "").strip()
        if not text:
            return
        answer = await self._answer(text)
        await update.message.reply_text(answer)

    async def _answer(self, text: str) -> str:
        """Route one message through the engine; never raises (bot keeps running)."""
        if self.model_manager is None:
            return "Aether model backend is not running. Check the /setup page."
        try:
            from aether.cognitive.service import run_cognitive_query

            answer = await run_cognitive_query(self.agent_id, text, self.model_manager)
            return answer or "(agent returned no answer)"
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Engine call failed in Telegram bridge")
            return f"(inference error: {exc})"