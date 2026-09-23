# Agent Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the agent runtime to manage the lifecycle, identity, and persistence of agents, enabling them to transition from IDLE to ACTIVE and back.

**Architecture:** The `AgentRuntime` acts as the coordinator. It uses the `LifecycleManager` to handle state transitions and the `Identity` domain objects to maintain persistence. It interfaces with the `ModelManager` for cognition and the `VectorStore` for memory.

**Tech Stack:** Python 3.11+, `asyncio`, SQLAlchemy, Pydantic.

**Spec:** docs/superpowers/specs/2026-09-23-aether-core-mvp-design.md

## Global Constraints
- Target RAM: $\leq$ 8 GB
- Identity: Must be stored in SQLite, not in prompts.
- Lifecycle: Explicit state machine (CREATED $\rightarrow$ INITIALIZED $\rightarrow$ IDLE $\rightarrow$ AWAKENED $\rightarrow$ ... $\rightarrow$ IDLE).
- Persistence: State must survive process restarts.

---

### Task 1: Identity & Personality Domain Models

**Files:**
- Create: `src/aether/agent/identity.py`
- Create: `src/aether/agent/personality.py`

**Interfaces:**
- Produces: `AgentIdentity` and `Personality` Pydantic models for internal runtime use.

- [ ] **Step 1: Implement `src/aether/agent/identity.py`**

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class AgentIdentity(BaseModel):
    agent_id: str
    name: str
    role: str
    personality: Dict[str, Any]
    skills: List[str]
    goals: List[str] = []
    preferences: Dict[str, Any] = {}
```

- [ ] **Step 2: Implement `src/aether/agent/personality.py`**

```python
from typing import Dict

class PersonalityManager:
    """
    Logic for mapping personality traits to prompt modifiers.
    """
    TRAIT_MODIFIERS = {
        "analytical": "Be concise, use bullet points, and prioritize logical reasoning.",
        "curious": "Ask clarifying questions and explore alternative possibilities.",
        "concise": "Provide the shortest possible correct answer."
    }

    @classmethod
    def get_modifier(cls, trait: str) -> str:
        return cls.TRAIT_MODIFIERS.get(trait, "")
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/agent/identity.py src/aether/agent/personality.py
git commit -m "feat: implement identity and personality domain models"
```

### Task 2: Lifecycle State Machine

**Files:**
- Create: `src/aether/agent/lifecycle.py`
- Test: `tests/unit/test_lifecycle.py`

**Interfaces:**
- Produces: `AgentState` Enum and `LifecycleManager` for transition validation.

- [ ] **Step 1: Implement `src/aether/agent/lifecycle.py`**

```python
from enum import Enum, auto
from typing import List

class AgentState(Enum):
    CREATED = auto()
    INITIALIZED = auto()
    IDLE = auto()
    AWAKENED = auto()
    THINKING = auto()
    ACTING = auto()
    OBSERVING = auto()
    REFLECTING = auto()
    LEARNING = auto()
    SLEEPING = auto()

class LifecycleManager:
    # Define valid transitions
    TRANSITIONS = {
        AgentState.CREATED: [AgentState.INITIALIZED],
        AgentState.INITIALIZED: [AgentState.IDLE],
        AgentState.IDLE: [AgentState.AWAKENED, AgentState.SLEEPING],
        AgentState.AWAKENED: [AgentState.THINKING, AgentState.IDLE],
        AgentState.THINKING: [AgentState.ACTING, AgentState.OBSERVING, AgentState.IDLE],
        AgentState.ACTING: [AgentState.OBSERVING, AgentState.IDLE],
        AgentState.OBSERVING: [AgentState.THINKING, AgentState.REFLECTING, AgentState.IDLE],
        AgentState.REFLECTING: [AgentState.LEARNING, AgentState.IDLE],
        AgentState.LEARNING: [AgentState.IDLE],
        AgentState.SLEEPING: [AgentState.AWAKENED, AgentState.IDLE],
    }

    @classmethod
    def validate_transition(cls, current: AgentState, next_state: AgentState) -> bool:
        return next_state in cls.TRANSITIONS.get(current, [])
```

- [ ] **Step 2: Write and run unit tests for `LifecycleManager`**

```python
# tests/unit/test_lifecycle.py
from aether.agent.lifecycle import AgentState, LifecycleManager

def test_valid_transitions():
    assert LifecycleManager.validate_transition(AgentState.CREATED, AgentState.INITIALIZED) is True
    assert LifecycleManager.validate_transition(AgentState.IDLE, AgentState.AWAKENED) is True

def test_invalid_transitions():
    assert LifecycleManager.validate_transition(AgentState.CREATED, AgentState.ACTING) is False
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/agent/lifecycle.py tests/unit/test_lifecycle.py
git commit -m "feat: implement agent lifecycle state machine"
```

### Task 3: Agent Runtime Core (Wake/Sleep)

**Files:**
- Create: `src/aether/agent/runtime.py`
- Test: `tests/unit/test_runtime.py`

**Interfaces:**
- Consumes: `LifecycleManager`, `AgentRepository`, `IdentityRepository`
- Produces: `AgentRuntime` class with `wake(agent_id)` and `sleep(agent_id)` methods.

- [ ] **Step 1: Implement `src/aether/agent/runtime.py`**

```python
from aether.agent.lifecycle import AgentState, LifecycleManager
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.database import AsyncSessionLocal
from aether.agent.identity import AgentIdentity

class AgentRuntime:
    def __init__(self):
        self.active_agents = {} # agent_id -> loaded_state

    async def wake(self, agent_id: str):
        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            id_repo = IdentityRepository(session)
            
            agent = await agent_repo.get(agent_id)
            if not agent:
                raise ValueError("Agent not found")
            
            identity_data = await id_repo.get_by_id(agent_id) # Need to add this method to repo
            identity = AgentIdentity(**identity_data)
            
            # Transition: IDLE -> AWAKENED
            if LifecycleManager.validate_transition(AgentState(agent.status), AgentState.AWAKENED):
                agent.status = AgentState.AWAKENED.name
                await session.commit()
            
            self.active_agents[agent_id] = {"identity": identity, "state": AgentState.AWAKENED}
            return identity

    async def sleep(self, agent_id: str):
        if agent_id not in self.active_agents:
            return

        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = await agent_repo.get(agent_id)
            
            # Transition: ... -> IDLE
            agent.status = AgentState.IDLE.name
            await session.commit()
        
        del self.active_agents[agent_id]
```

- [ ] **Step 2: Add `get_by_id` to `IdentityRepository` in `src/aether/storage/repositories.py`**

- [ ] **Step 3: Write and run tests for `AgentRuntime` wake/sleep cycle**

- [ ] **Step 4: Commit**

### Task 4: Goal & Skill Systems

**Files:**
- Create: `src/aether/agent/goals.py`
- Create: `src/aether/agent/skills.py`

**Interfaces:**
- Produces: `Goal` and `Skill` Pydantic models.

- [ ] **Step 1: Implement `src/aether/agent/goals.py`**

```python
from pydantic import BaseModel
from typing import List, Optional

class Goal(BaseModel):
    goal_id: str
    description: str
    priority: int
    status: str = "PENDING" # PENDING, IN_PROGRESS, COMPLETED, FAILED
    subgoals: List[str] = []
```

- [ ] **Step 2: Implement `src/aether/agent/skills.py`**

```python
from pydantic import BaseModel

class Skill(BaseModel):
    skill_id: str
    name: str
    description: str
    proficiency: float # 0.0 to 1.0
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/agent/goals.py src/aether/agent/skills.py
git commit -m "feat: implement goal and skill systems"
```

### Task 5: Integration Verification

- [ ] **Step 1: Verify that an agent can be created, awakened, and transitioned to IDLE.**
- [ ] **Step 2: Verify that agent state is correctly persisted in SQLite after sleep.**
- [ ] **Step 3: Commit**
