# Memory System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a five-tier memory system (L1-L5) that provides cognitive continuity for agents through a local-first vector store and a distillation pipeline.

**Architecture:** A `MemoryManager` coordinates between different memory tiers. L1 is volatile; L2-L5 are persistent. A `VectorStore` (NumPy/FAISS) handles semantic similarity, while SQLite handles episodic logs and semantic facts. The consolidation pipeline uses the LLM to distill raw experiences into durable knowledge.

**Tech Stack:** Python 3.11+, NumPy, FAISS (optional/local), SQLAlchemy, Pydantic.

**Spec:** docs/superpowers/specs/2026-09-23-aether-core-mvp-design.md

## Global Constraints
- Target RAM: $\leq$ 8 GB
- Storage: Local-first (no external vector DB for MVP).
- Distillation: Every experience is scored for importance before permanent storage.
- Continuity: Memory must be retrieved based on current context and agent goals.

---

### Task 1: Vector Store & Embeddings

**Files:**
- Create: `src/aether/memory/vector_store.py`
- Create: `src/aether/memory/embeddings.py`

**Interfaces:**
- Produces: `VectorStore` interface and `LocalVectorStore` implementation.
- Produces: `EmbeddingModel` wrapper.

- [ ] **Step 1: Implement `EmbeddingModel` wrapper**
  (Use a simple mock or a local sentence-transformer if available; default to a mock for MVP stability).
- [ ] **Step 2: Implement `VectorStore` ABC and `LocalVectorStore`**
  (Implement `add`, `search`, `delete` using NumPy arrays and cosine similarity).
- [ ] **Step 3: Implement local file persistence for vectors**
  (Save/Load NumPy arrays to disk).
- [ ] **Step 4: Commit**

### Task 2: The 5-Tier Infrastructure

**Files:**
- Create: `src/aether/memory/working.py`
- Create: `src/aether/memory/episodic.py`
- Create: `src/aether/memory/semantic.py`
- Create: `src/aether/memory/procedural.py`
- Create: `src/aether/memory/longterm.py`

**Interfaces:**
- Produces: Specific storage handlers for each tier.

- [ ] **Step 1: Implement L1 Working Memory**
  (Simple in-memory buffer for the current active session).
- [ ] **Step 2: Implement L2 Episodic Memory**
  (SQLite table: `episodic_memories` storing raw experience logs).
- [ ] **Step 3: Implement L3 Semantic Memory**
  (SQLite table for facts + VectorStore for semantic retrieval).
- [ ] **Step 4: Implement L4 Procedural Memory**
  (SQLite table for "how-to" steps and patterns).
- [ ] **Step 5: Implement L5 Long-Term Memory**
  (SQLite table for core identity and highly distilled insights).
- [ ] **Step 6: Commit**

### Task 3: Memory Retrieval Manager

**Files:**
- Create: `src/aether/memory/manager.py`

**Interfaces:**
- Consumes: All 5 tiers + `VectorStore`.
- Produces: `MemoryManager.retrieve(context, agent_id)` returning a consolidated context.

- [ ] **Step 1: Implement `MemoryManager` search logic**
  (Combine keyword search in SQLite and vector search in `LocalVectorStore`).
- [ ] **Step 2: Implement context assembly**
  (Rank and merge results from L2-L5 based on relevance).
- [ ] **Step 3: Commit**

### Task 4: Extraction & Importance Scoring

**Files:**
- Create: `src/aether/memory/extraction.py`
- Create: `src/aether/memory/importance.py`

**Interfaces:**
- Consumes: `ModelAdapter`.
- Produces: `extracted_facts` and `importance_score`.

- [ ] **Step 1: Implement `MemoryExtractor`**
  (Use the LLM to transform a raw experience into a list of facts/lessons).
- [ ] **Step 2: Implement `ImportanceScorer`**
  (Calculate score based on recurrence, goal alignment, and model-assigned weight).
- [ ] **Step 3: Commit**

### Task 5: Consolidation Pipeline

**Files:**
- Modify: `src/aether/memory/manager.py` (add `consolidate` method).

**Interfaces:**
- Consumes: `Experience` $\rightarrow$ `MemoryExtractor` $\rightarrow$ `ImportanceScorer` $\rightarrow$ `VectorStore`.

- [ ] **Step 1: Implement `consolidate_experience(experience)` flow**
  (Execute: Extract $\rightarrow$ Score $\rightarrow$ Tier Assignment $\rightarrow$ Store).
- [ ] **Step 2: Implement Tier Assignment logic**
  (Score $> X \rightarrow$ L5, Score $> Y \rightarrow$ L3, etc.).
- [ ] **Step 3: Commit**

### Task 6: Integration Verification

- [ ] **Step 1: Test "Experience $\rightarrow$ Memory" flow**
  (Verify that a task result is distilled into a semantic fact).
- [ ] **Step 2: Test "Context Retrieval"**
  (Verify that a laeter query retrieves the previously stored distilled fact).
- [ ], **Step 3: Commit**
