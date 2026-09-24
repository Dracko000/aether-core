# Aether Core

Aether Core is an autonomous cognitive engine designed for high-order reasoning, dynamic motivation, and self-evolving agent capabilities. Unlike traditional reactive agents, Aether utilizes a drive-based motivation system and a multi-hypothesis synthesis loop to navigate complex problem spaces.

## 🧠 Cognitive Architecture

### 1. Motivation Layer (Cognitive Drives)
Aether does not rely on static priority queues. It operates on internal cognitive pressures called **Drives**:
- **Curiosity**: Drives research, exploration, and discovery.
- **Coherence**: Drives the resolution of contradictions and synthesis of knowledge.
- **Stability**: Drives task completion, maintenance, and system finalization.

These drives dynamically weight goal priorities, allowing the agent to shift focus based on environmental stimuli (e.g., a discovery event spikes Curiosity, shifting priority toward research).

### 2. Deep Reasoning (Multi-Hypothesis Synthesis)
The reflection process is upgraded from linear processing to a convergent reasoning loop:
- **Hypothesis Generation**: Produces multiple competing interpretations of an experience.
- **Adversarial Critique**: Cross-evaluates hypotheses against established beliefs to eliminate logical weaknesses.
- **Convergence**: Synthesizes the most robust elements into a final, high-confidence belief update.

### 3. Knowledge Synthesis (Cognitive Insights)
Aether transforms simple memory retrieval into synthesized knowledge. Through **Cognitive Insights**, the system can link multiple disparate experience nodes into a single higher-order belief, enabling the agent to perceive patterns across diverse data points.

### 4. Autonomous Evolution
The system monitors its own reasoning requirements. When a task's cognitive complexity exceeds the current model's capability, Aether triggers an autonomous migration to a higher-capability model to ensure task success.

## 🛠 Tech Stack
- **Language**: Python 3.12+
- **Database**: SQLite / SQLAlchemy (Async)
- **Memory**: Tiered Memory Architecture (Working $\rightarrow$ Episodic $\rightarrow$ Semantic $\rightarrow$ Procedural $\rightarrow$ Long-Term)
- **Graph**: Experience Graph for associative memory retrieval

## 🚀 Quick Start

### Installation
```bash
git clone https://github.com/Dracko000/aether-core.git
cd aether-core
pip install -r requirements.txt
```

### Running the Engine
```bash
python -m aether.main
```

### 🤖 Telegram Bridge (Auto-Setup)
Chat with an Aether agent straight from Telegram — every message is routed to one fixed agent and answered by the local model (Ollama).

The console is a **Next.js app** (`web/`, 9Router-style shell). It is the only public surface; it proxies to the FastAPI backend (bot + engine) which runs on loopback:

| Service | Address | Role |
|---|---|---|
| `aether-web` (Next.js) | `0.0.0.0:8456` (public) | Console at `/setup`, proxies `/setup/status` + `/api/setup` |
| `aether.service` (FastAPI) | `127.0.0.1:8457` (internal) | Bot polling, engine, writes `.env` |

1. Start the backend, then the web console:
   ```bash
   python -m uvicorn aether.api.app:app --host 127.0.0.1 --port 8457
   cd web && npm install && npm run build && npm start   # standalone build on :8456
   ```
2. Open it from any browser using the VPS IP:
   ```
   http://<IP_VPS>:8456/setup
   ```
   Example: `http://169.58.159.131:8456/setup`.
3. Make sure port **8456** is open in the VPS firewall/security group (e.g. `ufw allow 8456`, or your cloud provider panel). The API on 8457 is loopback-only.
4. Get a token from **@BotFather** on Telegram, fill in the form (agent id, optional model, optional Telegram user ID to notify from @userinfobot), click **Save & Start Bot**. When the bot starts it sends an "agent ACTIVE" notice to that chat.

The auto-setup validates the token via `getMe`, writes `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_AGENT_ID`, `TELEGRAM_ENABLED=true`, optional `TELEGRAM_CHAT_ID`), then starts the bot as a server background task. `/setup/status` shows the live status anytime.

### 🚀 Deploy as a service (VPS/server, always-on)

```bash
# systemd units: aether.service (FastAPI, internal) + aether-web.service (Next.js, public)
systemctl enable --now aether.service        # start + auto-start on reboot
systemctl enable --now aether-web.service    # Next.js console, public :8456
systemctl status aether.service aether-web.service
journalctl -u aether-web.service -f          # follow console logs
```

`aether.service` runs `uvicorn aether.api.app:app --host 127.0.0.1 --port 8457` (reads `.env`), `Restart=always`. `aether-web.service` runs the Next.js standalone server (`web/.next/standalone/server.js`) with `PORT=8456` and `AETHER_API_BASE=http://127.0.0.1:8457`. After `npm run build`, copy the static assets into the standalone folder before deploying:

```bash
cd web && cp -r .next/static .next/standalone/.next/static
```

## 📈 Evolution Roadmap
- [x] v0.1 - Base Agent Runtime
- [x] v0.3 - Autonomous Goal Decomposer
- [x] v0.4 - Social Cognition & Inter-agent Communication
- [x] v0.5 - Model Migration & Capability Matrix
- [x] v0.6 - Cognitive Depth (Drives & Advanced Reasoning)
- [ ] v0.7 - Collective Memory & Swarm Intelligence
