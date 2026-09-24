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
Chat dengan agent Aether langsung dari Telegram — semua pesan diteruskan ke satu agent tetap dan dijawab lewat model lokal (Ollama).

1. Start API server:
   ```bash
   python -m uvicorn aether.api.app:app --host 0.0.0.0 --port 8456
   ```
2. Buka **http://localhost:8456/setup** di browser.
3. Dapatkan token dari **@BotFather** di Telegram, isi form (agent id, opsional model), klik **Save & Start Bot**.

Auto-setup memvalidasi token via `getMe`, menulis `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_AGENT_ID`, `TELEGRAM_ENABLED=true`), lalu menyalakan bot sebagai background task server. `/setup/status` menampilkan status kapan saja.

## 📈 Evolution Roadmap
- [x] v0.1 - Base Agent Runtime
- [x] v0.3 - Autonomous Goal Decomposer
- [x] v0.4 - Social Cognition & Inter-agent Communication
- [x] v0.5 - Model Migration & Capability Matrix
- [x] v0.6 - Cognitive Depth (Drives & Advanced Reasoning)
- [ ] v0.7 - Collective Memory & Swarm Intelligence
