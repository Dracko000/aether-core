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
    provider: str = ""        # model provider id (default: keep current)
    model: str = ""           # concrete model name (default: keep current)
    api_key: str = ""         # only needed when switching to a keyed provider
    action: str = "start"  # "start" | "stop"


# ----------------------------------------------------------------- responses
def _status(app) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    masked = ""
    if token:
        masked = f"{token[:5]}…{token[-4:]}" if len(token) > 10 else "(set)"
    chat_id = settings.TELEGRAM_CHAT_ID.strip()
    bot = getattr(app.state, "telegram_bot", None)
    from aether.model.factory import effective_model_name
    from aether.model.providers import get_provider

    provider = get_provider(settings.MODEL_PROVIDER)
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
        # model provider routing
        "model_provider": settings.MODEL_PROVIDER,
        "provider_label": provider.display_name if provider else settings.MODEL_PROVIDER,
        "model_name": effective_model_name(),
        "provider_needs_key": bool(provider and provider.api_key_env),
        "provider_key_configured": bool(
            provider and (os.environ.get(provider.api_key_env) or settings.PROVIDER_API_KEY)
        ),
        "allowlist_active": bool(settings.TELEGRAM_ALLOWED_USERS.strip()),
    }


@router.get("/setup/providers")
async def setup_providers():
    """Public provider catalogue for the console (never includes keys)."""
    from aether.model.providers import provider_options

    return {"providers": provider_options()}


_PAGE = """<!doctype html>
<html lang="en" class="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aether · Core Console</title>
<style>
 :root{
  /* 9Router palette (from decolua/9router src/app/globals.css) */
  --color-bg:#FDFAF6;--color-bg-alt:#F7F3EE;--color-surface:#ffffff;
  --color-surface-2:#f4f4f5;--color-surface-3:#e7e7e9;
  --color-sidebar:rgba(244,241,236,.85);
  --color-border:#e5e7eb;--color-border-subtle:#f1f1f3;
  --color-text-main:#0a0a0a;--color-text-muted:#6B7280;--color-text-subtle:#9CA3AF;
  --color-brand-500:#E56A4A;--color-brand-600:#cc5236;--color-brand-700:#a64027;
  --color-success:#10B981;--color-danger:#cf222e;--color-warning:#F59E0B;--color-info:#3B82F6;
  --radius-lg:14px;--radius:10px;
  --shadow-soft:0 1px 2px 0 rgba(0,0,0,.04);
  --shadow-elev:inset 0 1px 0 0 rgba(255,255,255,.8),0 1px 2px rgba(15,23,42,.04),0 12px 36px -8px rgba(15,23,42,.10);
  --shadow-warm:0 2px 12px -2px rgba(229,106,74,.18);
 }
 .dark{
  --color-bg:#1a1a1a;--color-bg-alt:#1F1F1E;--color-surface:#262626;
  --color-surface-2:#303030;--color-surface-3:#3a3a3a;
  --color-sidebar:rgba(30,30,30,.85);
  --color-border:#333333;--color-border-subtle:#2a2a2a;
  --color-text-main:#ededed;--color-text-muted:#9ca3af;--color-text-subtle:#6b7280;
  --color-success:#22c55e;--color-danger:#ef4444;--color-warning:#fbbf24;--color-info:#60a5fa;
  --shadow-soft:0 1px 2px 0 rgba(0,0,0,.3);
  --shadow-elev:inset 0 1px 0 0 rgba(255,255,255,.06),0 1px 2px rgba(0,0,0,.4),0 16px 48px -8px rgba(0,0,0,.55);
  --shadow-warm:0 2px 12px -2px rgba(229,106,74,.25);
 }
 *{box-sizing:border-box;margin:0;padding:0}
 html{color-scheme:light}.dark{color-scheme:dark}
 body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'SF Pro Text','SF Pro Display',system-ui,sans-serif;
  background:var(--color-bg);color:var(--color-text-main);-webkit-font-smoothing:antialiased;min-height:100vh}
 ::selection{background:rgba(229,106,74,.25);color:var(--color-brand-500)}
 button{-webkit-user-select:none;user-select:none;cursor:pointer}
 .app{display:flex;min-height:100vh}
 /* ---------------- sidebar (9router shell) ---------------- */
 .sidebar{width:288px;flex:0 0 288px;border-right:1px solid var(--color-border-subtle);
  background:var(--color-sidebar);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  display:flex;flex-direction:column;position:sticky;top:0;height:100vh}
 .traffic-lights{display:flex;gap:8px;padding:20px 24px 8px}
 .traffic-light{width:12px;height:12px;border-radius:50%}
 .tl-red{background:#FF5F56}.tl-yellow{background:#FFBD2E}.tl-green{background:#27C93F}
 .brand{display:flex;flex-direction:column;gap:12px;padding:16px 24px 20px}
 .brand-main{display:flex;align-items:center;gap:12px;text-decoration:none;color:inherit}
 .brand-logo{display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:10px;
  background:linear-gradient(135deg,var(--color-brand-500),var(--color-brand-700));box-shadow:var(--shadow-warm);flex:none}
 .brand-logo svg{width:20px;height:20px;stroke:#fff}
 .brand-name h1{font-size:17px;font-weight:600;letter-spacing:-.02em}
 .brand-name span{font-size:12px;color:var(--color-text-muted)}
 nav{flex:1;overflow-y:auto;padding:8px 16px;scrollbar-width:thin}
 .nav-label{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
  color:var(--color-text-muted);opacity:.6;padding:14px 12px 6px}
 .nav-item{display:flex;align-items:center;gap:12px;width:100%;padding:7px 12px;border-radius:8px;
  border:0;background:none;color:var(--color-text-muted);font-size:13px;font-weight:500;
  text-align:left;transition:all .15s}
 .nav-item svg{width:18px;height:18px;flex:none;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
 .nav-item:hover{background:var(--color-surface-2);color:var(--color-text-main)}
 .nav-item:hover svg{color:var(--color-brand-500)}
 .nav-item.active{background:rgba(229,106,74,.10);color:var(--color-brand-500)}
 .nav-item.active svg{stroke-width:2.4}
 .side-foot{padding:16px 24px;border-top:1px solid var(--color-border-subtle);font-size:11px;color:var(--color-text-subtle)}
 /* ---------------- header (9router shell) ---------------- */
 .main{flex:1;min-width:0;display:flex;flex-direction:column;
  background:linear-gradient(180deg,var(--color-bg-alt) 0%,var(--color-bg) 100%)}
 .header{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:12px 16px 10px 32px;border-bottom:1px solid var(--color-border-subtle);
  background:var(--color-surface);opacity:.97;backdrop-filter:blur(20px);position:sticky;top:0;z-index:20}
 .page-title{display:flex;align-items:center;gap:8px}
 .page-title svg{width:22px;height:22px;stroke:var(--color-brand-500);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
 .page-title h1{font-size:19px;font-weight:600;letter-spacing:-.02em;line-height:1.2}
 .page-title p{font-size:13px;color:var(--color-text-muted)}
 .header-right{display:flex;align-items:center;gap:8px;flex:none}
 .icon-btn{display:flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:8px;
  border:1px solid var(--color-border);background:var(--color-surface);color:var(--color-text-muted);transition:.15s}
 .icon-btn:hover{color:var(--color-brand-500);border-color:var(--color-brand-500)}
 .icon-btn svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
 .status-chip{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:999px;
  font-size:12px;font-weight:600;border:1px solid var(--color-border);background:var(--color-surface);white-space:nowrap}
 .status-chip .dot{width:8px;height:8px;border-radius:50%}
 .status-chip.on{color:var(--color-success);border-color:color-mix(in srgb,var(--color-success) 40%,transparent);background:color-mix(in srgb,var(--color-success) 10%,transparent)}
 .status-chip.on .dot{background:var(--color-success);box-shadow:0 0 8px var(--color-success)}
 .status-chip.off{color:var(--color-danger);border-color:color-mix(in srgb,var(--color-danger) 40%,transparent);background:color-mix(in srgb,var(--color-danger) 10%,transparent)}
 .status-chip.off .dot{background:var(--color-danger);box-shadow:0 0 8px var(--color-danger)}
 /* ---------------- content ---------------- */
 .content{padding:24px 32px 48px;max-width:1000px;width:100%}
 .view{display:none;animation:fadeIn .2s ease-out forwards}
 .view.active{display:block}
 @keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
 .banner{display:flex;gap:12px;align-items:center;padding:14px 18px;border-radius:var(--radius-lg);
  background:var(--color-surface);border:1px solid var(--color-border);box-shadow:var(--shadow-soft);margin-bottom:20px;font-size:13.5px}
 .banner .ico{font-size:17px;flex:none}
 .banner b{color:var(--color-text-main)}
 .banner.warn{border-color:color-mix(in srgb,var(--color-warning) 45%,transparent);background:color-mix(in srgb,var(--color-warning) 7%,var(--color-surface))}
 .banner.ok{border-color:color-mix(in srgb,var(--color-success) 45%,transparent);background:color-mix(in srgb,var(--color-success) 7%,var(--color-surface))}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
 .card{background:var(--color-surface);border-radius:var(--radius-lg);box-shadow:var(--shadow-elev);
  border:1px solid var(--color-border-subtle);padding:20px}
 .card h3{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--color-text-muted)}
 .card .big{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:21px;font-weight:700;margin-top:12px;letter-spacing:-.01em}
 .card .sub{font-size:12px;color:var(--color-text-muted);margin-top:6px;word-break:break-all}
 .card .row{display:flex;justify-content:space-between;gap:8px;font-size:12px;margin-top:12px;color:var(--color-text-muted)}
 .card .row b{color:var(--color-text-main);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:600;word-break:break-all;text-align:right}
 .badge{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:11px;font-weight:600}
 .badge.ok{color:var(--color-success);border:1px solid color-mix(in srgb,var(--color-success) 35%,transparent);background:color-mix(in srgb,var(--color-success) 10%,transparent)}
 .badge.bad{color:var(--color-danger);border:1px solid color-mix(in srgb,var(--color-danger) 35%,transparent);background:color-mix(in srgb,var(--color-danger) 10%,transparent)}
 .badge.mut{color:var(--color-text-muted);border:1px solid var(--color-border);background:var(--color-surface-2)}
 .badge .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
 /* ---------------- setup form ---------------- */
 .steps{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px;font-size:12.5px;color:var(--color-text-muted)}
 .step{display:flex;align-items:center;gap:7px}
 .step i{width:20px;height:20px;border-radius:50%;background:rgba(229,106,74,.14);border:1px solid rgba(229,106,74,.4);
  color:var(--color-brand-500);font-style:normal;font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center}
 .step b{color:var(--color-text-main)}
 form.card{max-width:560px;display:block}
 label{display:block;font-size:12.5px;font-weight:600;color:var(--color-text-muted);margin:14px 0 5px}
 label .hint{display:block;font-weight:400;font-size:11.5px;color:var(--color-text-subtle);margin-top:2px}
 input{width:100%;padding:9px 12px;border-radius:var(--radius);border:1px solid var(--color-border);
  background:var(--color-bg);color:var(--color-text-main);font-size:13px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;outline:none;transition:.15s}
 input:focus{border-color:var(--color-brand-500);box-shadow:0 0 0 3px rgba(229,106,74,.15)}
 input::placeholder{color:var(--color-text-subtle)}
 .btnrow{display:flex;gap:10px;margin-top:18px}
 .btn{border:1px solid var(--color-border);background:var(--color-surface);color:var(--color-text-main);
  padding:8px 16px;border-radius:var(--radius);font-size:13px;font-weight:600;transition:.15s}
 .btn:hover{border-color:var(--color-brand-500);color:var(--color-brand-500)}
 .btn.primary{background:linear-gradient(135deg,var(--color-brand-500),var(--color-brand-600));border-color:transparent;color:#fff}
 .btn.primary:hover{filter:brightness(1.06);color:#fff}
 .btn.danger{color:var(--color-danger);border-color:color-mix(in srgb,var(--color-danger) 40%,transparent);background:color-mix(in srgb,var(--color-danger) 8%,transparent)}
 .btn.danger:hover{color:var(--color-danger);filter:brightness(1.05)}
 pre{background:var(--color-bg-alt);border:1px solid var(--color-border);border-radius:var(--radius-lg);
  padding:14px;overflow:auto;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  color:var(--color-text-muted);margin-top:20px}
 pre.ok{color:var(--color-success)} pre.err{color:var(--color-danger)}
 @media (max-width:820px){
  .app{flex-direction:column}
  .sidebar{width:100%;flex:none;height:auto;position:static;flex-direction:row;align-items:center;gap:12px;padding:10px 16px}
  .traffic-lights{display:none}
  .brand{padding:0}.brand-name span{display:none}
  nav{display:flex;gap:6px;padding:0;overflow:visible}
  .nav-label{display:none}
  .side-foot{display:none}
  .content{padding:18px 16px 40px}
  .header{padding:10px 16px}
 }
</style></head><body>
<div class="app">
 <!-- ======================= SIDEBAR (9router shell) ======================= -->
 <aside class="sidebar">
  <div class="traffic-lights">
   <span class="traffic-light tl-red"></span><span class="traffic-light tl-yellow"></span><span class="traffic-light tl-green"></span>
  </div>
  <div class="brand">
   <div class="brand-main">
    <div class="brand-logo"><svg viewBox="0 0 24 24" fill="none"><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z"/></svg></div>
    <div class="brand-name"><h1>Aether</h1><span>v0.1.0</span></div>
   </div>
  </div>
  <nav>
   <p class="nav-label">Main</p>
   <button class="nav-item active" data-view="overview">
    <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>
    Overview</button>
   <button class="nav-item" data-view="setup">
    <svg viewBox="0 0 24 24"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>
    Setup</button>
   <p class="nav-label">System</p>
   <button class="nav-item" data-view="about">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    About</button>
  </nav>
  <div class="side-foot">Aether Core · local-first agent · public console</div>
 </aside>

 <!-- ======================= MAIN (9router shell) ======================= -->
 <main class="main">
  <header class="header">
   <div class="page-title">
    <span id="title-icon">
     <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>
    </span>
    <div><h1 id="page-title">Overview</h1><p id="page-sub">Telegram bridge · Ollama · one-time setup</p></div>
   </div>
   <div class="header-right">
    <span id="top-status" class="status-chip off"><span class="dot"></span>Bot offline</span>
    <button class="icon-btn" onclick="refresh()" title="Refresh">
     <svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/></svg>
    </button>
    <button class="icon-btn" id="theme-btn" title="Toggle theme">
     <svg id="theme-ico" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>
    </button>
   </div>
  </header>

  <div class="content">
   <!-- ============================ OVERVIEW ============================ -->
   <section class="view active" id="view-overview">
    <div class="banner warn" id="setup-banner" style="display:none">
     <span class="ico">⚙️</span>
     <div><b>First-time setup required.</b> Add your @BotFather token once — after that this console becomes a live monitor and you never touch it again.</div>
    </div>
    <div class="banner ok" id="live-banner" style="display:none">
     <span class="ico">✅</span>
     <div><b>Bridge is active.</b> Messages sent to your bot are routed to the agent automatically. No further setup needed — this console now just monitors status.</div>
    </div>
    <div class="grid">
     <div class="card">
      <h3>Telegram Bot</h3>
      <div class="big" id="val-bot">—</div>
      <div class="sub" id="val-bot-agent">agent —</div>
     </div>
     <div class="card">
      <h3>Model</h3>
      <div class="big" id="val-model">—</div>
      <div class="sub">backend <b style="color:var(--color-text-main)">Ollama</b> · local, no API key</div>
      <div class="row"><span>Base URL</span><b id="val-ollama">—</b></div>
     </div>
     <div class="card">
      <h3>Bot Token</h3>
      <div class="big" id="val-token">—</div>
      <div class="sub" id="val-token-masked">—</div>
     </div>
     <div class="card">
      <h3>Activation Notice</h3>
      <div class="big" id="val-notify">—</div>
      <div class="sub">notifies the owner chat when the agent goes live</div>
     </div>
    </div>
   </section>

   <!-- ============================ SETUP ============================ -->
   <section class="view" id="view-setup">
    <div class="steps">
     <span class="step"><i>1</i><b>@BotFather</b> → new bot → copy token</span>
     <span class="step"><i>2</i>Fill form &amp; Save (once)</span>
     <span class="step"><i>3</i>Chat with the bot — done</span>
    </div>
    <form class="card" id="setup">
     <h3>Create or update the bridge</h3>
     <label>Telegram Bot Token<span class="hint">from @BotFather</span></label>
     <input name="telegram_token" id="inp-token" placeholder="123456:ABC-DEF…" autocomplete="off" required>
     <label>Agent ID<span class="hint">all chats are routed to this agent</span></label>
     <input name="agent_id" id="inp-agent" placeholder="aria" required>
     <label>Model Provider<span class="hint">local Ollama or a remote API</span></label>
     <select name="provider" id="inp-provider"></select>
     <label>Model<span class="hint">optional — empty = provider default</span></label>
     <input name="model" id="inp-model" placeholder="e.g. qwen2.5:0.5b / gpt-4o-mini">
     <label>Provider API Key<span class="hint">remote providers only</span></label>
     <input name="api_key" id="inp-apikey" placeholder="sk-…" autocomplete="off">
     <label>Telegram user ID to notify when active<span class="hint">optional — get yours from @userinfobot</span></label>
     <input name="notify_chat_id" id="inp-notify" placeholder="123456789" autocomplete="off">
     <div class="btnrow">
      <button type="submit" class="btn primary">💾 Save &amp; Start Bot</button>
      <button type="button" class="btn danger" id="stop">🛑 Stop Bot</button>
     </div>
    </form>
    <pre id="result">– idle –</pre>
   </section>

   <!-- ============================ ABOUT ============================ -->
   <section class="view" id="view-about">
    <div class="grid">
     <div class="card" style="grid-column:1/-1">
      <h3>Aether Core · v0.1.0</h3>
      <p style="margin-top:12px;font-size:13.5px;color:var(--color-text-muted);line-height:1.65">
       Local-first agent runtime: one fixed agent answers every Telegram message through the
       cognitive engine, backed by a local model (Ollama) or a remote provider (OpenAI,
       Anthropic, OpenRouter, Groq, DeepSeek, xAI, Gemini) — mix-and-match from the Setup tab.
       Setup happens once here; this console
       (9Router-style shell) then monitors the live bridge. Docs and deploy notes live in the project README.</p>
     </div>
    </div>
   </section>
  </div>
 </main>
</div>
<script>
 const VIEWS=['overview','setup','about'];
 const topStatus=document.getElementById('top-status');
 let chosenProvider=null;
 const titles={overview:['Overview','Telegram bridge · Ollama · one-time setup'],
   setup:['Setup','Configure once — then it just runs'],
   about:['About','Aether Core console']};
 const icons={overview:'<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
   setup:'<svg viewBox="0 0 24 24"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>',
   about:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>'};
 function go(view){
  VIEWS.forEach(v=>{
   document.getElementById('view-'+v).classList.toggle('active',v===view);
   document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
  });
  document.getElementById('title-icon').innerHTML=icons[view];
  document.getElementById('page-title').textContent=titles[view][0];
  document.getElementById('page-sub').textContent=titles[view][1];
 }
 document.querySelectorAll('.nav-item').forEach(b=>b.onclick=()=>go(b.dataset.view));

 async function refresh(){
  let s;
  try{ s=await (await fetch('/setup/status')).json(); }
  catch(e){ setChip(topStatus,'off','Status offline'); return; }
  const on=s.bot_running;
  setChip(topStatus,on?'on':'off',on?'Bot running':'Bot stopped');
  document.getElementById('val-bot').innerHTML=on
   ?'<span class="badge ok"><span class="dot"></span>Running</span>':'<span class="badge bad"><span class="dot"></span>Stopped</span>';
  document.getElementById('val-bot-agent').textContent=s.token_configured
   ?'agent '+s.agent_id+' · token '+s.token_masked:'agent '+s.agent_id+' · no token';
  document.getElementById('val-model').textContent=(s.provider_label||s.model_provider||'—')+' · '+(s.model_name||'—');
  document.getElementById('val-ollama').textContent=s.ollama_base_url||'—';
  document.getElementById('val-token').innerHTML=s.token_configured
   ?'<span class="badge ok">Configured</span>':'<span class="badge bad">Missing</span>';
  document.getElementById('val-token-masked').textContent=s.token_configured?('token '+s.token_masked):'get one from @BotFather';
  document.getElementById('val-notify').innerHTML=s.notify_configured
   ?'<span class="badge ok">On</span>':'<span class="badge mut">Not set</span>';
  document.getElementById('setup-banner').style.display=(!s.token_configured||!s.bot_running)?'flex':'none';
  document.getElementById('live-banner').style.display=(s.token_configured&&s.bot_running)?'flex':'none';
  document.getElementById('inp-agent').value=s.agent_id||'';
  document.getElementById('inp-model').value=s.model_name||'';
  document.getElementById('inp-notify').value=s.notify_configured?s.notify_chat_id:'';
  const sel=document.getElementById('inp-provider');
  if(sel){
   if(sel.options.length===0){
    try{
     const p=await (await fetch('/setup/providers')).json();
     p.providers.forEach(pr=>{
      const o=document.createElement('option');
      o.value=pr.id;o.textContent=pr.display_name+(pr.key_configured?' ✓':'')+(pr.needs_key?' ⚠':' · local');
      sel.appendChild(o);
     });
    }catch(e){}
    sel.onchange=()=>{chosenProvider=sel.value;};
   }
   sel.value=chosenProvider||s.model_provider||'ollama';
  }
 }
 function setChip(el,cls,txt){el.className='status-chip '+cls;el.innerHTML='<span class="dot"></span>'+txt;}

 async function post(body){
  const r=await fetch('/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
 }
 document.getElementById('setup').onsubmit=async e=>{
  e.preventDefault();const f=new FormData(e.target);
  const j=await post({telegram_token:f.get('telegram_token'),agent_id:f.get('agent_id'),
    ollama_model:f.get('ollama_model'),provider:f.get('provider'),model:f.get('model'),
    api_key:f.get('api_key'),notify_chat_id:f.get('notify_chat_id'),action:'start'});
  const el=document.getElementById('result');
  el.textContent=JSON.stringify(j,null,2);
  el.className=j.ok?'ok':'err';
  if(j.ok){e.target.reset();document.getElementById('inp-agent').value=j.agent_id||'';}
  refresh();
 };
 document.getElementById('stop').onclick=async()=>{
  const j=await post({action:'stop'});
  const el=document.getElementById('result');
  el.textContent=JSON.stringify(j,null,2);el.className='ok';
  refresh();
 };

 /* theme toggle (9router-style, persisted) */
 const root=document.documentElement;
 const themeBtn=document.getElementById('theme-btn');
 const themeIco=document.getElementById('theme-ico');
 const SUN='<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>';
 const MOON='<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>';
 function applyTheme(dark){root.classList.toggle('dark',dark);themeIco.innerHTML=dark?MOON:SUN;localStorage.setItem('aether-theme',dark?'dark':'light');}
 themeBtn.onclick=()=>applyTheme(!root.classList.contains('dark'));
 applyTheme(localStorage.getItem('aether-theme')!=='light');

 refresh();
 setInterval(refresh,5000);
</script></body></html>"""


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

        # Model provider routing (optional — defaults keep the current config).
        from aether.model.providers import get_provider, provider_options

        provider_id = (req.provider or settings.MODEL_PROVIDER or "ollama").lower().strip()
        profile = get_provider(provider_id)
        if profile is None:
            known = ", ".join(p["id"] for p in provider_options())
            return {"ok": False, "error": f"Unknown provider {provider_id!r}. Known: {known}"}

        provider_changed = settings.MODEL_PROVIDER != provider_id
        model_changed = False
        if provider_id == "ollama" and req.model.strip():
            updates["MODEL_NAME"] = req.model.strip()
            model_changed = settings.MODEL_NAME != req.model.strip()
        elif provider_id != "ollama":
            if req.model.strip():
                updates["MODEL_NAME"] = req.model.strip()
                model_changed = settings.MODEL_NAME != req.model.strip()
            if profile.api_key_env:
                key = (req.api_key or "").strip()
                if key:
                    updates[profile.api_key_env] = key
                elif not (os.environ.get(profile.api_key_env) or settings.PROVIDER_API_KEY):
                    return {
                        "ok": False,
                        "error": (
                            f"Provider {profile.display_name} needs an API key "
                            f"(env {profile.api_key_env}) — get one at {profile.signup_url or 'its console'}."
                        ),
                    }
        updates["MODEL_PROVIDER"] = provider_id

        write_env(updates)

        # Reflect the new values in the in-process singleton immediately.
        settings.TELEGRAM_BOT_TOKEN = updates["TELEGRAM_BOT_TOKEN"]
        settings.TELEGRAM_AGENT_ID = agent_id
        settings.TELEGRAM_ENABLED = True
        if req.ollama_model.strip():
            settings.OLLAMA_MODEL = req.ollama_model.strip()
        settings.MODEL_PROVIDER = provider_id
        if "MODEL_NAME" in updates:
            settings.MODEL_NAME = updates["MODEL_NAME"]
        if profile.api_key_env and updates.get(profile.api_key_env):
            os.environ[profile.api_key_env] = updates[profile.api_key_env]
        if notify_chat_id:
            settings.TELEGRAM_CHAT_ID = notify_chat_id

        # Rebuild the model stack when provider/model switched so the bot (and
        # engine) talk to the newly selected backend.
        model_manager = getattr(app.state, "model_manager", None)
        if provider_changed or model_changed:
            from aether.model.factory import build_model_manager

            if model_manager is not None:
                await model_manager.shutdown()
            model_manager = build_model_manager()
            app.state.model_manager = model_manager

        from aether.model.factory import effective_model_name

        bot = await start_bot_in_app(app, settings.TELEGRAM_BOT_TOKEN, agent_id, model_manager)
        result = {
            "ok": True,
            "bot_running": True,
            "bot_username": token_info.get("username"),
            "bot_name": token_info.get("name"),
            "agent_id": agent_id,
            "model_provider": provider_id,
            "model_name": effective_model_name(),
            "note": "Config saved to .env. Bot is now polling in the background.",
        }

        # Notify the owner that the agent is now active.
        if notify_chat_id and bot is not None:
            try:
                await bot.send_message(
                    notify_chat_id,
                    f"✅ Aether agent '<b>{agent_id}</b>' is now <b>ACTIVE</b>.\n"
                    f"Provider: <b>{provider_id}</b> · Model: <b>{effective_model_name()}</b>\n"
                    f"Chat ready — send me a message!",
                )
                result["notification"] = f"activation notice sent to chat {notify_chat_id}"
            except Exception as exc:  # invalid chat id, bot restrictions, …
                logger.warning("Activation notice failed for chat %s: %s", notify_chat_id, exc)
                result["warning"] = f"Bot started, but the activation notice could not be sent: {exc}"
        return result
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Setup failed")
        return {"ok": False, "error": f"Setup error: {exc}"}