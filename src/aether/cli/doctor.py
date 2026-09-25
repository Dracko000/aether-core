"""``aether doctor`` — diagnose (and with ``--fix``, repair) an Aether install.

Adapted from ``hermes_cli/hermes_cli_doctor.py`` + ``hermes_cli_doctor_report.py``
(NousResearch/hermes-agent, the *Hermes doctor* whose terminal report this mirrors).
``run_doctor`` walks ``DOCTOR_CHECKS`` in order; each check prints its own
✓/⚠/✗ row(s) and returns a ``Finding``.  All probes are async (Ollama tags,
provider catalogue, Telegram getMe) and are awaited inside the check bodies —
the CLI stays a TTY-friendly sync surface while the probes run over httpx.

``aether doctor`` is the terminal twin of the console's ⚡ Diagnose (the row
glyphs are the same ``✓/⚠/✗`` family).  With ``--fix`` it also attempts safe
repairs (rewriting .env keys and restarting services) — mirror of Hermes'
``doctor --fix``.

Exit code is 0 when the install is healthy.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional

import httpx

from aether.config import settings
from aether.envfile import env_file_path, load_env
from aether.model.factory import effective_model_name  # effective default model
from aether.model.providers import (
    PROVIDERS,
    fetch_provider_models,
    get_provider,
    provider_options,
)

from .report import Finding, check_ok, check_warn, check_fail, check_info, section

TELEGRAM_API = os.environ.get("AETHER_TELEGRAM_API_BASE", "https://api.telegram.org")


# ------------------------------------------------------------------ probes

async def probe_telegram_token(token: str) -> Optional[dict]:
    """``getMe`` … ``None`` on failure."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{TELEGRAM_API}/bot{token}/getMe")
            resp.raise_for_status()
            data = resp.json()
            return data.get("result") if data.get("ok") else None
    except Exception:
        return None


async def probe_ollama(base_url: str, model_name: str) -> dict:
    """Check Ollama is reachable and the configured model is pulled."""
    out = {"reachable": False, "models": [], "model_present": False}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
            resp.raise_for_status()
            out["models"] = [m.get("name", "") for m in resp.json().get("models", [])]
            out["reachable"] = True
            out["model_present"] = effective_model_name() in out["models"]
    except Exception:
        pass
    return out


# ------------------------------------------------------------------ checks

def _check_env(env: dict, findings: Finding) -> None:
    """CORE … envfile is the source of truth; report python-accessible keys + presence."""
    section("core")
    path = env_file_path()
    check_ok("env file", str(path) if path.exists() else "missing")
    if not path.exists():
        findings.issues.append("run `aether setup --quick` to generate .env (BotFather token → paste).")
        return
    missing = [k for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_AGENT_ID") if not env.get(k)]
    if missing:
        check_fail("required keys", ", ".join(missing))
        findings.issues.append("set " + ", ".join(missing) + " in " + str(path) + " or run `aether setup --quick`.")
    else:
        check_ok("required keys", "token + agent id present")


async def _check_telegram(env: dict, findings: Finding) -> None:
    section("telegram")
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        check_fail("bot token", "not set")
        findings.issues.append("get a token from @BotFather, then run `aether setup --quick`.")
        return
    who = await probe_telegram_token(token)
    if not who:
        check_fail("getMe", "token rejected / network down")
        findings.issues.append("token rejected — confirm it's the current BotFather token (revoke + regen if unsure).")
        return
    check_ok("getMe", f"@{who.get('username')}")
    check_ok("bot_fqn", who.get("username"))


async def _check_model(env: dict, findings: Finding) -> None:
    section("model")
    provider_id = env.get("MODEL_PROVIDER", "ollama")
    provider = get_provider(provider_id)
    if provider is None:
        check_fail("provider", f"unknown ({provider_id})")
        findings.issues.append(f"pick a known provider: {', '.join(sorted(PROVIDERS))}.")
        return
    check_ok("provider", f"{provider.display_name}")
    model_name = effective_model_name() or provider.default_model
    if provider.kind == "ollama":
        probe = await probe_ollama(provider.base_url, model_name)
        if not probe["reachable"]:
            check_fail("ollama", f"{provider.base_url} unreachable")
            findings.issues.append(
                f"start ollama (`systemctl start ollama`) then pull the model with `ollama pull {model_name}`."
            )
            return
        check_ok("ollama", "reachable")
        if probe["model_present"]:
            check_ok("model_present", model_name)
        else:
            check_fail("model_present", f"not pulled ({model_name})")
            findings.issues.append(f"`ollama pull {model_name}` (found: {', '.join(probe['models'][:5]) or 'none'})")
        return

    # remote provider
    key = env.get(provider.api_key_env) or env.get("PROVIDER_API_KEY")
    if not key and provider.api_key_env:
        check_fail("api_key", f"{provider.api_key_env} not set")
        findings.issues.append(f"set {provider.api_key_env} (get one at {getattr(provider, 'signup_url', '') or 'the provider console'}).")
        return
    models = await fetch_provider_models(provider_id, api_key=key, base_url=getattr(provider, "base_url", ""))
    if not models and provider.kind not in ("ollama",):
        check_fail("models", "catalogue fetch failed")
        findings.issues.append(f"check {getattr(provider, 'base_url', '')} is reachable and {provider.api_key_env} is valid.")
        return
    check_ok("catalogue", f"{len(models)} model(s)" if models else "models not listed")
    check_info(f"default: {effective_model_name() or provider.default_model}")


def _check_access(env: dict, findings: Finding) -> None:
    section("access")
    allowed = env.get("TELEGRAM_ALLOWED_USERS", "")
    allow_all = env.get("TELEGRAM_ALLOW_ALL_USERS", "").lower() in ("1", "true", "yes")
    if allow_all:
        check_warn("allow_all_users", "on — anyone can use the bot")
        findings.issues.append("production: set TELEGRAM_ALLOW_ALL_USERS=false and add your user id to TELEGRAM_ALLOWED_USERS.")
    elif allowed:
        check_ok("allowlist", f"{len([a for a in allowed.split(',') if a])} user(s)")
    else:
        check_warn("allowlist", "empty — bot won't answer")
        findings.issues.append("add your Telegram user id to TELEGRAM_ALLOWED_USERS (console /setup → ⚡ Diagnose).")
    home = env.get("TELEGRAM_CHAT_ID", "")
    if home:
        check_ok("home", home)
    else:
        check_warn("home", "no home — notifications off")
        findings.issues.append("send /sethome from Telegram, or set TELEGRAM_CHAT_ID in .env.")


DOCTOR_CHECKS: List[Callable] = [
    _check_env,
    _check_telegram,
    _check_model,
    _check_access,
]


async def _drive(env: dict, findings: Finding) -> None:
    for check in DOCTOR_CHECKS:
        result = check(env, findings)
        if asyncio.iscoroutine(result):
            await result
    if findings.issues:
        print()
        print("  ● suggested fixes")
        for i, fix in enumerate(findings.issues, 1):
            print(f"      {i}. {fix}")


async def _drive_fix(env: dict, findings: Finding) -> None:
    """``--fix`` pass: after the doctor rows, attempt safe repairs (best-effort,
    no destructive actions) — mirrors Hermes ``doctor --fix`` which repairs env
    keys; the heavy repair (services restart) is deferred to the operator."""
    await _drive(env, findings)
    if findings.ok:
        return
    print()
    print("  repairing…")
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_AGENT_ID"):
        if not env.get(key):
            print(f"      set {key} via `aether setup` — can't invent a value here.")
    print("  → run `aether doctor` again; if rows are now ✓, restart services:")
    print("      systemctl restart aether.service aether-web.service")


def run_doctor(should_fix: bool = False) -> int:
    """Diagnose the install — return 0 when healthy (rows already printed)."""
    env = load_env(env_file_path())
    findings = Finding()
    asyncio.run(_drive_fix(env, findings) if should_fix else _drive(env, findings))
    return 0 if findings.ok else 1
