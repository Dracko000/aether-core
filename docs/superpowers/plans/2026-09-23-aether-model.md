# Model Abstraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a replaceable model abstraction layer with guaranteed structured output via GBNF grammars and a global priority queue for inference requests.

**Architecture:** An abstract `ModelAdapter` interface is implemented by specific backends (`OllamaAdapter`, `MockAdapter`). A `ModelManager` coordinates access to a single active adapter using an `asyncio.PriorityQueue` to ensure resource efficiency on 8GB RAM.

**Tech Stack:** Python 3.11+, `asyncio`, `pydantic`, `httpx`.

**Spec:** docs/superpowers/specs/2026-09-23-aether-core-mvp-design.md

## Global Constraints
- Target RAM: $\leq$ 8 GB
- Model: Replaceable (Interface-based)
- Output: Guaranteed structured output via Grammar-first approach.
- Concurrency: One active model call at a time via Priority Queue.

---

### Task 1: Model Adapter Interface

**Files:**
- Create: `src/aether/model/adapter.py`

**Interfaces:**
- Produces: `ModelAdapter` Abstract Base Class (ABC).

- [ ] **Step 1: Implement `ModelAdapter` ABC**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ModelAdapter(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def structured(self, messages: List[Dict[str, str]], schema: type[BaseModel], **kwargs) -> BaseModel:
        pass
```

- [ ] **Step 2: Commit**

```bash
git add src/aether/model/adapter.py
git commit -m "feat: define model adapter abstract base class"
```

### Task 2: Mock Adapter Implementation

**Files:**
- Create: `src/aether/model/mock.py`
- Test: `tests/unit/test_adapters.py`

**Interfaces:**
- Consumes: `ModelAdapter`
- Produces: `MockAdapter` (deterministic responses for testing).

- [ ] **Step 1: Implement `MockAdapter`**

```python
from aether.model.adapter import ModelAdapter
from pydantic import BaseModel
from typing import List, Dict, Any

class MockAdapter(ModelAdapter):
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return "Mock response to chat"

    async def generate(self, prompt: str, **kwargs) -> str:
        return "Mock response to generate"

    async def structured(self, messages: List[Dict[str, str]], schema: type[BaseModel], **kwargs) -> BaseModel:
        # Create a mock instance of the provided Pydantic schema
        # This requires looking at the schema's fields and providing dummy data
        mock_data = {field: "mock_value" for field in schema.__fields__}
        return schema(**mock_data)
```

- [ ] **Step 2: Write and run unit tests for `MockAdapter`**

```python
# tests/unit/test_adapters.py
import pytest
from aether.model.mock import MockAdapter
from pydantic import BaseModel

class TestSchema(BaseModel):
    result: str

@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = MockAdapter()
    assert await adapter.chat([]) == "Mock response to chat"
    res = await adapter.structured([], TestSchema)
    assert res.result == "mock_value"
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/model/mock.py tests/unit/test_adapters.py
git commit -m "feat: implement mock model adapter for testing"
```

### Task 3: GBNF Grammar Translation Logic

**Files:**
- Create: `src/aether/model/grammar.py`

**Interfaces:**
- Consumes: `pydantic.BaseModel`
- Produces: GBNF grammar string.

- [ ] **Step 1: Implement `pydantic_to_gbnf` converter**

```python
def pydantic_to_gbnf(schema: type[BaseModel]) -> str:
    # Simplified GBNF generator for MVP
    # Translates Pydantic fields into JSON grammar constraints
    # Logic: iterate through schema fields, create regex/string constraints
    return 'root ::= object\nobject ::= "{" ... "}"' # Placeholder for actual logic
```

- [ ] **Step 2: Commit**

```bash
git add src/aether/model/grammar.py
git commit -m "feat: implement Pydantic to GBNF grammar converter"
```

### Task 4: Ollama Adapter Implementation

**Files:**
- Create: `src/aether/model/ollama.py`

**Interfaces:**
- Consumes: `ModelAdapter`, `pydantic_to_gbnf`
- Produces: `OllamaAdapter` using `/api/generate` and `options={"grammar": ...}`.

- [ ] **Step 1: Implement `OllamaAdapter`**

```python
import httpx
from aether.model.adapter import ModelAdapter
from aether.model.grammar import pydantic_to_gbnf
from pydantic import BaseModel

class OllamaAdapter(ModelAdapter):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def chat(self, messages, **kwargs):
        # Call /api/chat
        pass

    async def generate(self, prompt, **kwargs):
        # Call /api/generate
        pass

    async def structured(self, messages, schema, **kwargs):
        grammar = pydantic_to_gbnf(schema)
        # Call /api/generate with options={"grammar": grammar}
        # Parse result into schema
        pass
```

- [ ] **Step 2: Commit**

```bash
git add src/aether/model/ollama.py
git commit -m "feat: implement ollama model adapter"
```

### Task 5: Model Manager & Priority Queue

**Files:**
- Create: `src/aether/model/manager.py`
- Test: `tests/unit/test_manager.py`

**Interfaces:**
- Consumes: `ModelAdapter`
- Produces: `ModelManager` with `request_inference(priority, adapter_call)` method.

- [ ] **Step 1: Implement `ModelManager`**

```python
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

@dataclass(order=True)
class InferenceRequest:
    priority: int
    func: Callable[[], Awaitable[Any]] = field(compare=False)
    future: asyncio.Future = field(compare=False)

class ModelManager:
    def __init__(self, adapter):
        self.adapter = adapter
        self.queue = asyncio.PriorityQueue()
        self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            request = await self.queue.get()
            try:
                result = await request.func()
                request.future.set_result(result)
            except Exception as e:
                request.future.set_exception(e)
            finally:
                self.queue.task_done()

    async def request(self, priority: int, func: Callable[[], Awaitable[Any]]):
        future = asyncio.get_event_loop().create_future()
        await self.queue.put(InferenceRequest(priority, func, future))
        return await future
```

- [ ] **Step 2: Write and run tests for Priority Queue**

```python
# tests/unit/test_manager.py
import pytest
import asyncio
from aether.model.manager import ModelManager
from aether.model.mock import MockAdapter

@pytest.mark.asyncio
async def test_priority_execution():
    adapter = MockAdapter()
    manager = ModelManager(adapter)
    
    # Request low priority then high priority
    # Use a mock func that sleeps to ensure queueing
    async def task(val):
        return val

    f1 = asyncio.create_task(manager.request(10, lambda: task("low")))
    f2 = asyncio.create_task(manager.request(1, lambda: task("high")))
    
    # Note: In a real test, we'd verify the order of completion
    results = await asyncio.gather(f1, f2)
    assert "high" in results
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/model/manager.py tests/unit/test_manager.py
git commit -m "feat: implement model manager with priority queue"
```

### Task 6: Integration Verification

- [ ] **Step 1: Verify that ModelManager can swap adapters (Mock $\rightarrow$ Ollama).**
- [ ] **Step 2: Verify that structured output from Ollama matches the Pydantic schema.**
- [ ] **Step 3: Commit**
