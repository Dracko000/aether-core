"""Auto-setup page: configure the Telegram bridge from the browser.

``GET /setup`` renders a small web form (token from @BotFather, agent id,
optional model override). ``POST /setup`` validates the token via the Bot
API, checks the Ollama backend, writes the values into the env file, reloads
the in-process settings, and (re)starts the long-polling bot as a background
task of the API server.

Infrastructure hooks kept at module scope so tests can redirect them:
- ``AETHER_ENV_FILE`` overrides the env file path.
- ``AETHER_TELEGRAM_API_BASE`` overrides the Bot API base URL.
"""
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from aether.config import settings

logger = logging.getLogger("aether.setup")
router = APIRouter(tags=["setup"])

_TELEGRAM_API = os.environ.get("AETHER_TELEGRAM_API_BASE", "https://api.telegram.org")


# ---------------------------------------------------------------- env file
def env_file_path() -> Path:
    return Path(os.environ.get("AETHER_ENV_FILE", ".env"))


def load_env(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip()
    return data


def write_env(updates: Dict[str, str], path: Optional[Path] = None) -> Path:
    """Merge ``updates`` into the env file, preserving unrelated keys."""
    path = path or env_file_path()
    data = load_env(path)
    data.update({k: v for k, v in updates.items() if v is not None})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k}={v}\n" for k, v in data.items()))
    return path


# --------------------------------------------------------------- validators
async def check_telegram_token(token: str) -> dict:
    """Validate a bot token via the Telegram getMe endpoint."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{_TELEGRAM_API}/bot{token}/getMe")
    except Exception as exc:  # network errors
        return {"ok": False, "detail": f"cannot reach Telegram API: {exc}"}
    if resp.status_code != 200:
        return {"ok": False, "detail": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    data = resp.json()
    if not data.get("ok"):
        return {"ok": False, "detail": data.get("description", "token rejected")}
    user = data.get("result", {})
    return {
        "ok": True,
        "username": user.get("username"),
        "name": user.get("first_name"),
    }


async def check_ollama(base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/api/tags")
    except Exception as exc:
        return {"ok": False, "detail": f"cannot reach Ollama: {exc}"}
    if resp.status_code != 200:
        return {"ok": False, "detail": f"HTTP {resp.status_code}"}
    models = [m.get("name") for m in resp.json().get("models", []) or []]
    return {"ok": True, "models": models}


# ------------------------------------------------------------ bot lifecycle
async def start_bot_in_app(app, token: str, agent_id: str, model_manager):
    """Create, persist and start the polling bot; attach it to ``app.state``."""
    from aether.bot.telegram import AetherTelegramBot

    await stop_bot_in_app(app)
    bot = AetherTelegramBot(token, agent_id, model_manager)
    await bot.start()
    app.state.telegram_bot = bot
    return bot


async def stop_bot_in_app(app) -> None:
    bot = getattr(app.state, "telegram_bot", None)
    if bot is not None:
        await bot.stop()
    app.state.telegram_bot = None


# ------------------------------------------------------------------- models
class SetupRequest(BaseModel):
    telegram_token: str = ""
    agent_id: str = "aria"
    ollama_model: str = ""
    notify_chat_id: str = ""
    action: str = "start"  # "start" | "stop"


# ----------------------------------------------------------------- responses
def _status(app) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    masked = ""
    if token:
        masked = f"{token[:5]}…{token[-4:]}" if len(token) > 10 else "(set)"
    chat_id = settings.TELEGRAM_CHAT_ID.strip()
    bot = getattr(app.state, "telegram_bot", None)
    return {
        "telegram_enabled": settings.TELEGRAM_ENABLED,
        "token_configured": bool(token),
        "token_masked": masked,
        "agent_id": settings.TELEGRAM_AGENT_ID,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "bot_running": bot is not None,
        "notify_configured": bool(chat_id),
        "notify_chat_id": chat_id if len(chat_id) <= 12 else f"{chat_id[:3]}…{chat_id[-2:]}",
    }


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Aether · Telegram auto-setup</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;background:#0f1420;color:#e6ebf5}
 h1{font-size:1.35rem} label{display:block;margin:14px 0 4px;font-weight:600}
 input{width:100%;padding:9px;border-radius:8px;border:1px solid #2c3652;background:#161d2e;color:#e6ebf5;box-sizing:border-box}
 button{margin-top:18px;padding:10px 18px;border:0;border-radius:8px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer}
 button.secondary{background:#334155;margin-left:8px}
 pre{background:#161d2e;border:1px solid #2c3652;border-radius:8px;padding:12px;overflow:auto;font-size:.85rem}
 .ok{color:#34d399}.err{color:#f87171}.info{color:#93c5fd}
</style></head><body>
<h1>⚡ Aether · Telegram Bot Auto-Setup</h1>
<p class="info">1. Get a token from <b>@BotFather</b> · 2. Fill the form · 3. Save &amp; Start — the bot runs as a server background task.</p>
<div id="status" class="info">Loading status…</div>
<form id="setup"><label>Telegram Bot Token</label>
<input name="telegram_token" placeholder="123456:ABC-DEF…" autocomplete="off" required>
<label>Agent ID (all chats are routed to this agent)</label>
<input name="agent_id" placeholder="aria" required>
<label>Model (optional — leave empty to use OLLAMA_MODEL)</label>
<input name="ollama_model" placeholder="qwen2.5:0.5b">
<label>Telegram user ID to notify when active (optional — get yours from <b>@userinfobot</b>)</label>
<input name="notify_chat_id" placeholder="123456789" autocomplete="off">
<div><button type="submit">💾 Save &amp; Start Bot</button>
<button type="button" class="secondary" id="stop">🛑 Stop Bot</button></div></form>
<pre id="result">–</pre>
<script>
 async function refresh(){
  const r=await fetch('/setup/status');const s=await r.json();
  document.getElementById('status').innerHTML=
   `<b>Status:</b> bot ${s.bot_running?'<span class="ok">running</span>':'<span class="err">stopped</span>'}
   · token ${s.token_configured?'<span class="ok">configured</span>':'<span class="err">missing</span>'} (${s.token_masked})
   · agent <b>${s.agent_id}</b> · ollama <b>${s.ollama_model}</b> @ ${s.ollama_base_url}`;
 }
 async function post(body){
  const r=await fetch('/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json(); return j;
 }
 document.getElementById('setup').onsubmit=async e=>{
  e.preventDefault();const f=new FormData(e.target);
  const j=await post({telegram_token:f.get('telegram_token'),agent_id:f.get('agent_id'),
                     ollama_model:f.get('ollama_model'),notify_chat_id:f.get('notify_chat_id'),action:'start'});
  document.getElementById('result').textContent=JSON.stringify(j,null,2);
  document.getElementById('result').className=j.ok?'ok':'err'; refresh();
 };
 document.getElementById('stop').onclick=async()=>{
  const j=await post({action:'stop'});refresh();
 };
 refresh();
</script></body></html>
"""


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    return HTMLResponse(_PAGE)


@router.get("/setup/status")
async def setup_status(request: Request):
    return _status(request.app)


@router.post("/setup")
async def setup_apply(request: Request, req: SetupRequest):
    app = request.app
    try:
        if req.action == "stop":
            await stop_bot_in_app(app)
            write_env({"TELEGRAM_ENABLED": "false"})
            settings.TELEGRAM_ENABLED = False
            return {"ok": True, "bot_running": False}

        if not req.telegram_token.strip():
            return {"ok": False, "error": "Telegram bot token is required (ask @BotFather)."}

        token_info = await check_telegram_token(req.telegram_token.strip())
        if not token_info["ok"]:
            return {"ok": False, "error": f"Token rejected by Telegram: {token_info['detail']}"}

        agent_id = req.agent_id.strip() or settings.TELEGRAM_AGENT_ID
        notify_chat_id = req.notify_chat_id.strip()
        updates = {
            "TELEGRAM_BOT_TOKEN": req.telegram_token.strip(),
            "TELEGRAM_AGENT_ID": agent_id,
            "TELEGRAM_ENABLED": "true",
        }
        if req.ollama_model.strip():
            updates["OLLAMA_MODEL"] = req.ollama_model.strip()
        if notify_chat_id:
            updates["TELEGRAM_CHAT_ID"] = notify_chat_id

        write_env(updates)

        # Reflect the new values in the in-process singleton immediately.
        settings.TELEGRAM_BOT_TOKEN = updates["TELEGRAM_BOT_TOKEN"]
        settings.TELEGRAM_AGENT_ID = agent_id
        settings.TELEGRAM_ENABLED = True
        if req.ollama_model.strip():
            settings.OLLAMA_MODEL = req.ollama_model.strip()
        if notify_chat_id:
            settings.TELEGRAM_CHAT_ID = notify_chat_id

        model_manager = getattr(app.state, "model_manager", None)
        bot = await start_bot_in_app(app, settings.TELEGRAM_BOT_TOKEN, agent_id, model_manager)
        result = {
            "ok": True,
            "bot_running": True,
            "bot_username": token_info.get("username"),
            "bot_name": token_info.get("name"),
            "agent_id": agent_id,
            "note": "Token saved to .env. Bot is now polling in the background.",
        }

        # Notify the owner that the agent is now active.
        if notify_chat_id and bot is not None:
            try:
                await bot.send_message(
                    notify_chat_id,
                    f"✅ Aether agent '<b>{agent_id}</b>' is now <b>ACTIVE</b>.\n"
                    f"Model: {settings.OLLAMA_MODEL} · Chat ready — send me a message!",
                )
                result["notification"] = f"activation notice sent to chat {notify_chat_id}"
            except Exception as exc:  # invalid chat id, bot restrictions, …
                logger.warning("Activation notice failed for chat %s: %s", notify_chat_id, exc)
                result["warning"] = f"Bot started, but the activation notice could not be sent: {exc}"
        return result
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Setup failed")
        return {"ok": False, "error": f"Setup error: {exc}"}