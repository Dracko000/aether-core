"""``aether setup`` — interactive quick-setup wizard (terminal twin of the web
console at ``[IP]:8456/setup``).  Adapted from ``hermes_cli_setup_quick`` +
``hermes_cli_setup.py`` (hermes-agent): only prompt for **missing** env keys,
write them into the env file, and leave everything else untouched.

Scope is intentionally narrow: this operator CLI fills in ``.env`` and pokes a
couple of live probes, nothing else.  The long-running work is owned by the
API services (``aether.service`` + ``aether-web.service``), not by this CLI.
"""

from __future__ import annotations

import getpass
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aether.envfile import env_file_path, load_env, write_env
from aether.model.factory import effective_model_name  # effective default model
from aether.model.providers import (
    PROVIDERS,
    fetch_provider_models,
    get_provider,
    provider_options,
)

BOTFATHER_URL = "https://t.me/BotFather"
_SKIP = object()


# ------------------------------------------------------------------ prompts

def _ask(text: str, default: str = "", *, secret: bool = False) -> str:
    prompt = f"  {text}"
    if default:
        prompt += f"  [{default}]"
    prompt += ": "
    try:
        if secret:
            return getpass.getpass(prompt).strip()
        return input(prompt).strip() or default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def _is_token(value: str) -> bool:
    """BotFather tokens look like ``123456789:AAHash…``."""
    return bool(re.fullmatch(r"\d{6,12}:[A-Za-z0-9_-]{30,}", value or ""))


def _provider_choice(env: dict) -> str:
    """Return a provider id, choosing a default from what's already set."""
    current = env.get("MODEL_PROVIDER", "").lower()
    options = provider_options()
    ids = [o["id"] for o in options]
    if current not in ids:
        current = "ollama" if "ollama" in ids else (ids[0] if ids else "")
    print()
    print("  model provider (enter to keep default):")
    for opt in options:
        mark = "  ← current" if opt["id"] == current else ""
        print(f"    {opt['id']:<16}{opt.get('display_name', '')}{mark}")
    choice = _ask("MODEL_PROVIDER", current).strip().lower()
    return choice if choice in ids else current


def _fetch_remote_models(provider_id: str, api_key: str, env: dict) -> List[Dict]:
    """Best-effort live model catalogue for the provider (async under the hood)."""
    import asyncio

    async def _go():
        try:
            return await fetch_provider_models(
                provider_id, api_key=api_key, base_url=env.get("MODEL_BASE_URL")
            )
        except Exception:
            return []

    try:
        return asyncio.run(_go())
    except Exception:
        return []


async def _probe_token(token: str) -> Optional[Dict]:
    """``getMe`` against the Bot API via a lightweight probe (no FastAPI)."""
    import httpx

    base = os.environ.get("AETHER_TELEGRAM_API_BASE", "https://api.telegram.org")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base}/bot{token}/getMe")
            resp.raise_for_status()
            data = resp.json()
            return data.get("result") if data.get("ok") else None
    except Exception:
        return None


# ------------------------------------------------------------------- wizard

def gather_missing(env: dict) -> Dict[str, str]:
    """Ask for everything missing; return only the (key → value) updates."""
    updates: Dict[str, str] = {}
    missing_required = [k for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_AGENT_ID") if not env.get(k)]

    if "TELEGRAM_BOT_TOKEN" in missing_required:
        print()
        print(f"  1) Telegram bot token — create a bot at {BOTFATHER_URL} (BotFather → /newbot).")
        print("     The token looks like ``123456789:AAHASH…`` and is shown once by BotFather.")
        while True:
            token = _ask("paste TELEGRAM_BOT_TOKEN", secret=True)
            if not token:
                print("     ⚠ no token → not saved; rerun `aether setup` when you have one.")
                break
            if not _is_token(token):
                print("     ⚠ doesn't look like a Bot token — double check BotFather output.")
                continue
            updates["TELEGRAM_BOT_TOKEN"] = token
            break

    if "TELEGRAM_AGENT_ID" in missing_required:
        agent = _ask("TELEGRAM_AGENT_ID (short name the bot greets you with)", default="aria")
        if agent:
            updates["TELEGRAM_AGENT_ID"] = agent

    # ---- provider
    provider_id = _provider_choice(env)
    updates["MODEL_PROVIDER"] = provider_id
    profile = get_provider(provider_id)

    if profile is not None and profile.api_key_env and not env.get(profile.api_key_env):
        signup = getattr(profile, "signup_url", "") or getattr(profile, "signup_url", "")
        print()
        print(f"  {profile.display_name} needs an API key — get one at: {signup or 'the provider console'}")
        key = _ask(profile.api_key_env, secret=True)
        if key:
            updates[profile.api_key_env] = key
            # quick live probe: does the key let us list models?
            models = _fetch_remote_models(provider_id, key, env)
            if models:
                print(f"     ✓ {len(models)} model(s) listed — key looks valid.")
            else:
                print("     ⚠ couldn't fetch models (key may need time, or endpoint may differ) — continuing.")

    model = effective_model_name() or (profile.default_model if profile else "")
    if not env.get("MODEL_NAME"):
        name = _ask(f"MODEL_NAME (enter to keep default)", default=model)
        if name:
            updates["MODEL_NAME"] = name

    # ---- access / home (optional, non-blocking)
    chat = env.get("TELEGRAM_CHAT_ID", "")
    if not chat:
        print()
        print("  Home chat (optional): used for proactive notifications. Leave empty to skip")
        print("  — you can also send /sethome in Telegram once the bot is running.")
        home = _ask("TELEGRAM_CHAT_ID")
        if home:
            updates["TELEGRAM_CHAT_ID"] = home

    return updates


def quick_setup(env: dict) -> Dict[str, str]:
    """``aether setup --quick`` — only missing keys, no catalogue probes."""
    updates: Dict[str, str] = {}
    if not env.get("TELEGRAM_BOT_TOKEN"):
        token = _ask("TELEGRAM_BOT_TOKEN", secret=True)
        if token:
            updates["TELEGRAM_BOT_TOKEN"] = token
    if not env.get("TELEGRAM_AGENT_ID"):
        updates["TELEGRAM_AGENT_ID"] = _ask("TELEGRAM_AGENT_ID", "aria") or "aria"
    if not env.get("MODEL_PROVIDER"):
        updates["MODEL_PROVIDER"] = _provider_choice(env)
    return updates


def run(env: dict, *, quick: bool = False) -> int:
    """Run the wizard, write updates, rerun ``aether doctor``. Return exit code.

    Returns 0 when done (even if some fields were skipped); a non-fatal path.
    """
    updates = quick_setup(env) if quick else gather_missing(env)
    if not updates:
        print("  nothing missing — `.env` already set. Run `aether doctor` to verify.")
        return 0
    write_env(updates)
    print()
    print(f"  ✓ wrote {len(updates)} key(s) to {env_file_path()}")
    print("  Restart the services to pick them up:")
    print("      systemctl restart aether.service aether-web.service")
    print("  Then open the console at http://<server-ip>:8456/setup and hit ⚡ Diagnose.")
    return 0
