"""``aether status`` — one-screen operator snapshot (adapted from ``hermes status``
+ the doctor report footer).  Pure env-file read; no API / network hops, so it
works even when the services are down.
"""

from __future__ import annotations

import os
from typing import Optional

from aether.config import settings
from aether.envfile import env_file_path, load_env
from aether.model.factory import effective_model_name


def _row(label: str, value: str, *, ok: Optional[bool] = None) -> None:
    mark = "✓" if ok else ("✗" if ok is False else "·")
    print(f"  {mark} {label:<24}{value}")


def print_status(env: dict) -> None:
    """Print the snapshot; no return (exit handled by caller)."""
    path = env_file_path()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    token_ok = bool(token)

    print()
    print("  aether status")
    print(f"  {'─' * 46}")
    _row("env file", str(path), ok=path.exists())
    _row("bot token", f"{token[:6]}…{token[-4:]}" if token else "—", ok=token_ok)
    _row("agent id", env.get("TELEGRAM_AGENT_ID") or "—", ok=bool(env.get("TELEGRAM_AGENT_ID")))
    provider = env.get("MODEL_PROVIDER", "ollama")
    model = effective_model_name() or settings.OLLAMA_MODEL
    _row("model", f"{provider} / {model}" if model else provider)
    _row("chat", env.get("TELEGRAM_CHAT_ID") or "— (use /sethome)", ok=bool(env.get("TELEGRAM_CHAT_ID")))
    allow = env.get("TELEGRAM_ALLOWED_USERS", "")
    _row("allowlist", allow or "— (not locked)", ok=bool(allow))

    print()
    print("  run `aether doctor` for a deep probe, or open the console:")
    print("      http://<server-ip>:8456/setup")
