# Aether Core MVP Design Specification
**Date:** 2026-09-23
**Status:** Finalized Design
**Version:** 1.0

## 1. Executive Summary
Aether Core is a lightweight, local-first cognitive foundation for persistent AI agents. It decouples cognition (the LLM) from agency (the runtime) and continuity (memory and identity). The goal is to provide a system where agents are persistent entities that survive process restarts and model replacements.

## 2. System Architecture
The system follows a layered approach to ensure modularity and replaceability.

### 2.1 Component Stack
1.  **API/CLI Layer:** FastAPI backend and a Python-based CLI.
2.  **Agent Runtime:** Manages agent lifecycles, state transitions, and the global inference priority queue.
3.  **Cognitive Engine:** Orchestrates the pipeline of perception, memory retrieval, reasoning, planning, and reflection.
4.  **Model Adapter:** A strict abstraction layer that converts Pydantic schemas into GBNF grammars for guaranteed structured output.
5.  **Rust Sandbox:** A hardened, separate process for the execution of high-risk tools (Shell, Code) via a local socket.
6.  **Persistent State:** SQLite for relational data (identities, goals, events) and a file-based NumPy/FAISS store for vector embeddings.

### 2.2 Data Flow (The Thought Cycle)
`Event` $\rightarrow$ `Wake Agent` $\rightarrow$ `Context Assembly (L1-L5 Memory)` $\rightarrow$ `Inference Queue` $\rightarrow$ `Grammar-Constrained Model Call` $\rightarrow$ `Tool Proposal` $\rightarrow$ `Permission Check` $\rightarrow$ `Rust Sandbox Execution` $\rightarrow$ `Observation` $\rightarrow$ `Verification` $\rightarrow$ `Reflection` $\rightarrow$ `Memory Consolidation` $\rightarrow$ `Sleep`.

## 3. Detailed Subsystems

### 3.1 Agent Identity & Lifecycle
Agents are defined by a persistent identity in SQLite, not a prompt.

**Identity Model:**
- `agent_id`, `name`, `role`
- `personality_traits` (analytical, curious, etc.)
- `skills` list
- `global_goals`

**Lifecycle State Machine:**
`CREATED` $\rightarrow$ `INITIALIZED` $\rightarrow$ `IDLE` $\rightarrow$ `AWAKENED` $\rightarrow$ `THINKING` $\rightarrow$ `ACTING` $\rightarrow$ `OBSERVING` $\rightarrow$ `REFLECTING` $\rightarrow$ `LEARNING` $\rightarrow$ `IDLE`.

### 3.2 Memory System
A five-tier architecture for cognitive continuity.

- **L1: Working Memory:** Current task context (volatile).
- **L2: Episodic Memory:** Log of events and raw experiences.
- **L3: Semantic Memory:** Persistent facts and concepts.
- **L4: Procedural Memory:** "How-to" knowledge for tasks.
- **L5: Long-Term Memory:** Highly distilled core identities and critical insights.

**Consolidation Pipeline:**
`Experience` $\rightarrow$ `Extraction (Model)` $\rightarrow$ `Importance Scoring (Heuristic)` $\rightarrow$ `Embedding` $\rightarrow$ `Tiered Storage`.

### 3.3 Model Runtime & Structured Output
The model is treated as a commodity.

- **Grammar-First Output:** The `ModelAdapter` translates Pydantic schemas into GBNF grammars. This guarantees that the LLM output is always valid JSON matching the expected schema.
- **Inference Priority Queue:** A global queue manages access to the shared model backend. Requests are sorted by `(Priority, Timestamp)`.

### 3.4 Rust Sandbox & Security
Security is enforced outside the model.

- **Isolation:** The Rust sandbox executes high-risk tools in a restricted environment with resource limits (`setrlimit`) and a command safe-list.
- **Permissions:** A `Permission Matrix` in SQLite defines which agents can access which tools. The Python Runtime rejects unauthorized tool proposals before they reach the sandbox.

### 3.5 Cognitive Engine Pipeline
The engine selects a path based on complexity:

- **Fast Path:** Simple conversation; bypasses planning and reflection.
- **Slow Path:** Complex tasks; utilizes the `Plan` $\rightarrow$ `Act` $\rightarrow$ `Observe` $\rightarrow$ `Verify` $\rightarrow$ `Reflect` loop.

## 4. Technical Stack
- **Language:** Python 3.11+ (Core), Rust (Sandbox).
- **API:** FastAPI.
- **Database:** SQLite (via SQLAlchemy).
- **Vector Store:** NumPy/FAISS (file-based).
- **Model Support:** Ollama, llama.cpp (GGUF).
- **Memory Limit:** Targeted for $\leq$ 8 GB RAM environments.

## 5. Success Criteria for MVP
1.  **Persistence:** Agent state (Identity, Memory, Goals) must survive a full process restart.
2.  **Isolation:** Multiple agents must share one model but have isolated memories.
3.  **Reliability:** Structured output must be guaranteed via GBNF.
4.  **Security:** Unauthorized tool calls must be blocked by the runtime.
5.  **Continuity:** An agent must recover its previous state and continue a task after waking.
