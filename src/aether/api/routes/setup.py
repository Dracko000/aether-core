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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aether · Core Console</title>
<style>
 :root{--bg:#0b0f1a;--panel:#10162a;--panel2:#0d1322;--line:#1e2740;--txt:#e6ebf5;--mut:#8b96b5;
       --acc:#3b82f6;--acc2:#22d3ee;--ok:#34d399;--err:#f87171;--warn:#fbbf24;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
 *{box-sizing:border-box;margin:0;padding:0}
 body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--txt);min-height:100vh}
 .app{display:flex;min-height:100vh}
 /* ---------- sidebar ---------- */
 .sidebar{width:232px;flex:0 0 232px;background:linear-gradient(180deg,#0d1322,#0a0e1a);border-right:1px solid var(--line);
   display:flex;flex-direction:column;padding:18px 14px;position:sticky;top:0;height:100vh}
 .brand{display:flex;gap:10px;align-items:center;padding:2px 6px 18px;border-bottom:1px solid var(--line);margin-bottom:14px}
 .logo{font-size:22px;filter:drop-shadow(0 0 8px rgba(59,130,246,.7))}
 .brand b{font-size:15px;letter-spacing:.4px}
 .brand small{display:block;color:var(--mut);font-size:10.5px;letter-spacing:1.4px;text-transform:uppercase}
 nav{display:flex;flex-direction:column;gap:4px;flex:1}
 .nav-item{display:flex;align-items:center;gap:10px;background:none;border:1px solid transparent;color:var(--mut);
   padding:10px 12px;border-radius:10px;cursor:pointer;font-size:13.5px;font-weight:600;text-align:left;transition:.15s}
 .nav-item svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
 .nav-item:hover{color:var(--txt);background:#141b30}
 .nav-item.active{color:#fff;background:rgba(59,130,246,.14);border-color:rgba(59,130,246,.35)}
 .side-foot{padding:12px 8px 0;border-top:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}
 /* ---------- main ---------- */
 .main{flex:1;display:flex;flex-direction:column;min-width:0}
 .topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 28px;
   border-bottom:1px solid var(--line);background:rgba(16,22,42,.6);backdrop-filter:blur(6px);position:sticky;top:0;z-index:5}
 .topbar h1{font-size:19px;font-weight:700}
 .topbar p{color:var(--mut);font-size:12.5px;margin-top:2px}
 .actions{display:flex;gap:10px;align-items:center}
 .pill{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:.3px}
 .pill .dot{width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor}
 .pill.on{color:var(--ok);background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.35)}
 .pill.off{color:var(--err);background:rgba(248,113,113,.10);border:1px solid rgba(248,113,113,.3)}
 .pill.warn{color:var(--warn);background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.3)}
 .btn{border:1px solid var(--line);background:#161d30;color:var(--txt);padding:8px 14px;border-radius:9px;
   font-size:13px;font-weight:600;cursor:pointer;transition:.15s}
 .btn:hover{background:#1b2440;border-color:#2c3a5e}
 .btn.primary{background:var(--acc);border-color:var(--acc);color:#fff}
 .btn.primary:hover{background:#2f6fe0}
 .btn.danger{background:rgba(248,113,113,.12);border-color:rgba(248,113,113,.4);color:var(--err)}
 .btn.ghost{background:none}
 .content{padding:26px 28px 40px;max-width:1060px;width:100%}
 .view{display:none;animation:fade .25s ease}
 .view.active{display:block}
 @keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
 /* ---------- cards ---------- */
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
 .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;position:relative;overflow:hidden}
 .card::before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--acc),transparent);opacity:.65}
 .card h3{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:var(--mut);font-weight:700;display:flex;align-items:center;gap:8px}
 .card .big{font-size:22px;font-weight:700;margin-top:12px;font-family:var(--mono);letter-spacing:.3px}
 .card .sub{color:var(--mut);font-size:12px;margin-top:6px;word-break:break-all}
 .card .row{display:flex;justify-content:space-between;font-size:12.5px;margin-top:10px;color:var(--mut)}
 .card .row b{color:var(--txt);font-family:var(--mono);font-weight:600}
 .badge{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700}
 .badge.ok{color:var(--ok);background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.3)}
 .badge.bad{color:var(--err);background:rgba(248,113,113,.10);border:1px solid rgba(248,113,113,.3)}
 .badge.mut{color:var(--mut);background:#141b30;border:1px solid var(--line)}
 .banner{display:flex;gap:12px;align-items:center;background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.3);
   border-radius:12px;padding:14px 16px;margin-bottom:18px;font-size:13.5px}
 .banner.warn{background:rgba(251,191,36,.07);border-color:rgba(251,191,36,.3)}
 .banner .ico{font-size:18px}
 /* ---------- setup form ---------- */
 form.card{max-width:560px;display:block}
 label{display:block;font-size:12.5px;font-weight:600;color:var(--mut);margin:14px 0 5px;letter-spacing:.2px}
 input{width:100%;padding:10px 12px;border-radius:9px;border:1px solid var(--line);background:var(--panel2);
   color:var(--txt);font-size:13.5px;font-family:var(--mono);outline:none;transition:.15s}
 input:focus{border-color:var(--acc);box-shadow:0 0 0 3px rgba(59,130,246,.18)}
 input::placeholder{color:#4a5575}
 .hint{font-size:11.5px;color:var(--mut);margin-top:4px}
 pre{background:#080c16;border:1px solid var(--line);border-radius:12px;padding:14px;overflow:auto;
   font-size:12px;font-family:var(--mono);color:#9fb4e8;margin-top:16px;white-space:pre-wrap}
 pre.ok{color:var(--ok)} pre.err{color:var(--err)}
 .btnrow{display:flex;gap:10px;margin-top:18px}
 .steps{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:18px;font-size:12.5px;color:var(--mut)}
 .steps span b{color:var(--txt)}
 .step{display:flex;align-items:center;gap:7px}
 .step i{width:20px;height:20px;border-radius:50%;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.4);
   color:var(--acc2);font-style:normal;font-weight:700;font-size:11px;display:flex;align-items:center;justify-content:center}
 @media (max-width:780px){
  .app{flex-direction:column}
  .sidebar{width:100%;height:auto;flex-direction:row;align-items:center;padding:12px 16px;position:static;gap:14px}
  .brand{border:0;margin:0;padding:0}
  nav{flex-direction:row;flex:1}
  .nav-item{padding:8px 10px;font-size:12px}
  .side-foot{border:0;padding:0}
  .content{padding:18px 16px 32px}
  .topbar{padding:14px 16px}
 }
</style></head><body>
<div class="app">
 <aside class="sidebar">
  <div class="brand"><span class="logo">⚡</span><div><b>Aether</b><small>Core Console</small></div></div>
  <nav>
   <button class="nav-item active" data-view="overview">
    <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>
    Overview</button>
   <button class="nav-item" data-view="setup">
    <svg viewBox="0 0 24 24"><path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.09a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>
    Setup</button>
   <button class="nav-item" data-view="about">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
    About</button>
  </nav>
  <div class="side-foot">
   <span id="side-status" class="pill off"><span class="dot"></span>Offline</span>
   <small style="color:var(--mut);font-family:var(--mono)">v0.1.0</small>
  </div>
 </aside>

 <main class="main">
  <header class="topbar">
   <div><h1 id="page-title">Overview</h1><p id="page-sub">Telegram bridge · Ollama · one-time setup</p></div>
   <div class="actions">
    <span id="top-status" class="pill off"><span class="dot"></span>Bot offline</span>
    <button class="btn ghost" onclick="refresh()">↻ Refresh</button>
   </div>
  </header>

  <div class="content">
   <!-- ============================ OVERVIEW ============================ -->
   <section class="view active" id="view-overview">
    <div class="banner warn" id="setup-banner" style="display:none">
     <span class="ico">⚙️</span>
     <div><b>First-time setup required.</b> Add your @BotFather token once — after that this page becomes a live monitor and you never need to touch it again.</div>
    </div>
    <div class="banner" id="live-banner" style="display:none">
     <span class="ico">✅</span>
     <div><b>Bridge is active.</b> Messages sent to your bot are routed to the agent automatically. No further setup needed — this page now just monitors status.</div>
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
      <div class="sub">backend <b style="color:var(--txt)">Ollama</b> · local, no API key</div>
      <div class="row"><span>Base URL</span><b id="val-ollama">—</b></div>
     </div>
     <div class="card">
      <h3>Bot Token</h3>
      <div class="big" id="val-token">—</div>
      <div class="sub" id="val-token-masked" style="font-family:var(--mono)">—</div>
     </div>
     <div class="card">
      <h3>Activation Notice</h3>
      <div class="big" id="val-notify">—</div>
      <div class="sub">notifies owner chat when agent goes live</div>
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
     <label>Telegram Bot Token</label>
     <input name="telegram_token" id="inp-token" placeholder="123456:ABC-DEF…" autocomplete="off" required>
     <label>Agent ID <span class="hint">all chats are routed to this agent</span></label>
     <input name="agent_id" id="inp-agent" placeholder="aria" required>
     <label>Model <span class="hint">optional — leave empty to use OLLAMA_MODEL</span></label>
     <input name="ollama_model" id="inp-model" placeholder="qwen2.5:0.5b">
     <label>Telegram user ID to notify when active <span class="hint">optional — get yours from @userinfobot</span></label>
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
      <p style="margin-top:10px;font-size:13.5px;color:var(--mut);line-height:1.6">
       Local agent runtime: one fixed agent answers every Telegram message through the
       cognitive engine, backed by a fully local model (Ollama) — no API keys, no cloud.
       Setup happens once via the <b style="color:var(--txt)">Setup</b> tab; this console then
       monitors the live bridge. Docs and deploy notes live in the project README.</p>
     </div>
    </div>
   </section>
  </div>
 </main>
</div>
<script>
 const VIEWS=['overview','setup','about'];
 const topStatus=document.getElementById('top-status');
 const sideStatus=document.getElementById('side-status');
 function go(view){
  VIEWS.forEach(v=>{
   document.getElementById('view-'+v).classList.toggle('active', v===view);
   document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active', b.dataset.view===view));
  });
  const t={overview:['Overview','Telegram bridge · Ollama · one-time setup'],
           setup:['Setup','Configure once — then it just runs'],
           about:['About','']}[view];
  document.getElementById('page-title').textContent=t[0];
  document.getElementById('page-sub').textContent=t[1];
 }
 document.querySelectorAll('.nav-item').forEach(b=>b.onclick=()=>go(b.dataset.view));

 async function refresh(){
  let s;
  try{ s=await (await fetch('/setup/status')).json(); }
  catch(e){ setPill(topStatus,'off','Status offline'); return; }
  const on=s.bot_running;
  setPill(topStatus, on?'on':'off', on?'● Bot running':'● Bot stopped');
  setPill(sideStatus, on?'on':'off', on?'Online':'Offline');
  document.getElementById('val-bot').innerHTML=on
   ?'<span class="badge ok">● Running</span>':'<span class="badge bad">● Stopped</span>';
  document.getElementById('val-bot-agent').textContent=s.token_configured
   ?'agent '+s.agent_id+' · token '+s.token_masked:'agent '+s.agent_id+' · no token';
  document.getElementById('val-model').textContent=s.ollama_model||'—';
  document.getElementById('val-ollama').textContent=s.ollama_base_url||'—';
  document.getElementById('val-token').innerHTML=s.token_configured
   ?'<span class="badge ok">Configured</span>':'<span class="badge bad">Missing</span>';
  document.getElementById('val-token-masked').textContent=s.token_configured?('token '+s.token_masked):'get one from @BotFather';
  document.getElementById('val-notify').innerHTML=s.notify_configured
   ?'<span class="badge ok">On</span>':'<span class="badge mut">Not set</span>';
  document.getElementById('setup-banner').style.display=(!s.token_configured||!s.bot_running)?'flex':'none';
  document.getElementById('live-banner').style.display=(s.token_configured&&s.bot_running)?'flex':'none';
  go(VIEWS.find(v=>document.getElementById('view-'+v).classList.contains('active'))||'overview');
  // prefill editable fields (no token — never leak it back)
  document.getElementById('inp-agent').value=s.agent_id||'';
  document.getElementById('inp-model').value=s.ollama_model==='llama3'?'':s.ollama_model||'';
  document.getElementById('inp-notify').value=s.notify_configured?s.notify_chat_id:'';
 }
 function setPill(el,cls,txt){el.className='pill '+cls;el.innerHTML='<span class="dot"></span>'+txt;}

 async function post(body){
  const r=await fetch('/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
 }
 document.getElementById('setup').onsubmit=async e=>{
  e.preventDefault();const f=new FormData(e.target);
  const j=await post({telegram_token:f.get('telegram_token'),agent_id:f.get('agent_id'),
    ollama_model:f.get('ollama_model'),notify_chat_id:f.get('notify_chat_id'),action:'start'});
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
 refresh();
 setInterval(refresh,5000);
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