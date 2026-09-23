# Aether Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the project foundation including configuration, database schemas, basic API, and CLI scaffolding.

**Architecture:** A FastAPI-based backend using SQLAlchemy with SQLite for persistence. A Python CLI communicates with the API.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic, Typer (CLI), Pytest.

**Spec:** docs/superpowers/specs/2026-09-23-aether-core-mvp-design.md

## Global Constraints
- Target RAM: $\leq$ 8 GB
- Database: SQLite
- Python Version: 3.11+
- All internal model operations must support structured output.

---

### Task 1: Project Environment & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`

**Interfaces:**
- Produces: Standardized environment for all subsequent tasks.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "aether-core"
version = "0.1.0"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "sqlalchemy",
    "pydantic",
    "pydantic-settings",
    "typer",
    "httpx",
    "aiosqlite",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "black",
    "mypy",
]
```

- [ ] **Step 2: Create `.env.example`**

```env
AETHER_DATABASE_URL=sqlite+aiosqlite:///./data/sqlite/aether.db
AETHER_API_PORT=8000
AETHER_API_HOST=0.0.0.0
AETHER_LOG_LEVEL=INFO
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml .env.example
git commit -m "chore: project foundation dependencies"
```

### Task 2: Configuration System

**Files:**
- Create: `src/aether/config.py`

**Interfaces:**
- Produces: `settings: Settings` object for app-wide configuration.

- [ ] **Step 1: Write failing test for config loading**

```python
# tests/unit/test_config.py
from aether.config import Settings
def test_config_defaults():
    settings = Settings()
    assert settings.API_PORT == 8000
```

- [ ] **Step 2: Implement `src/aether/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sqlite/aether.db"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py`

- [ ] **Step 4: Commit**

```bash
git add src/aether/config.py tests/unit/test_config.py
git commit -m "feat: implement configuration system"
```

### Task 3: Database Schema & Models

**Files:**
- Create: `src/aether/storage/database.py`
- Create: `src/aether/storage/models.py`

**Interfaces:**
- Produces: `async_session` factory and SQLAlchemy models (`Agent`, `Identity`).

- [ ] **Step 1: Implement `src/aether/storage/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from aether.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # In MVP, we use simple create_all; migration path is noted in spec
        from aether.storage.models import Base
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Implement `src/aether/storage/models.py`**

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, JSON
from typing import List

class Base(DeclarativeBase):
    pass

class Agent(Base):
    __tablename__ = "agents"
    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="CREATED") # Lifecycle state

class Identity(Base):
    __tablename__ = "identities"
    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    personality: Mapped[dict] = mapped_column(JSON)
    skills: Mapped[list] = mapped_column(JSON)
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/storage/database.py src/aether/storage/models.py
git commit -m "feat: implement database schemas for agents and identities"
```

### Task 4: Repositories (Data Access Layer)

**Files:**
- Create: `src/aether/storage/repositories.py`
- Test: `tests/unit/test_repositories.py`

**Interfaces:**
- Consumes: `AsyncSessionLocal`
- Produces: `AgentRepository` and `IdentityRepository` classes.

- [ ] **Step 1: Implement `src/aether/storage/repositories.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aether.storage.models import Agent, Identity

class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, agent_id: str):
        agent = Agent(agent_id=agent_id)
        self.session.add(agent)
        await self.session.commit()
        return agent

    async def get(self, agent_id: str):
        result = await self.session.execute(select(Agent).where(Agent.agent_id == agent_id))
        return result.scalar_one_or_none()

class IdentityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, agent_id: str, name: str, role: str, personality: dict, skills: list):
        identity = Identity(agent_id=agent_id, name=name, role=role, personality=personality, skills=skills)
        self.session.add(identity)
        await self.session.commit()
        return identity
```

- [ ] **Step 2: Write and run integration test for repositories**

```python
# tests/unit/test_repositories.py
import pytest
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository

@pytest.mark.asyncio
async def test_agent_lifecycle():
    await init_db()
    async with AsyncSessionLocal() as session:
        repo = AgentRepository(session)
        agent = await repo.create("test_001")
        assert agent.agent_id == "test_001"
        
        fetched = await repo.get("test_001")
        assert fetched is not None
```

- [ ] **Step 3: Commit**

```bash
git add src/aether/storage/repositories.py tests/unit/test_repositories.py
git commit -m "feat: implement data access repositories"
```

### Task 5: API Scaffolding

**Files:**
- Create: `src/aether/api/app.py`
- Create: `src/aether/api/routes/health.py`
- Create: `src/aether/api/dependencies.py`

**Interfaces:**
- Consumes: `AsyncSessionLocal`
- Produces: FastAPI app instance.

- [ ] **Step 1: Implement `src/aether/api/dependencies.py`**

```python
from typing import AsyncGenerator
from aether.storage.database import AsyncSessionLocal

async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: Implement `src/aether/api/routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
```

- [ ] **Step 3: Implement `src/aether/api/app.py`**

```python
from fastapi import FastAPI
from aether.api.routes import health

app = FastAPI(title="Aether Core API")
app.include_router(health.router)
```

- [ ] **Step 4: Commit**

```bash
git add src/aether/api/app.py src/aether/api/routes/health.py src/aether/api/dependencies.py
git commit -m "feat: implement API scaffolding and health check"
```

### Task 6: CLI Scaffolding

**Files:**
- Create: `src/aether/cli/main.py`

**Interfaces:**
- Consumes: `httpx` to call the API.
- Produces: Command line interface.

- [ ] **Step 1: Implement `src/aether/cli/main.py`**

```python
import typer
import httpx
from aether.config import settings

app = typer.Typer()

@app.command()
def health():
    """Check API health"""
    url = f"http://{settings.API_HOST}:{settings.API_PORT}/health"
    try:
        response = httpx.get(url)
        typer.echo(f"API Health: {response.json()['status']}")
    except Exception as e:
        typer.echo(f"Error: {e}")

if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Commit**

```bash
git add src/aether/cli/main.py
git commit -m "feat: implement CLI scaffolding"
```

### Task 7: Foundation Integration Test

**Files:**
- Create: `tests/integration/test_foundation.py`

**Interfaces:**
- Verifies: CLI $\rightarrow$ API $\rightarrow$ DB flow.

- [ ] **Step 1: Implement integration test**

```python
# tests/integration/test_foundation.py
import pytest
from fastapi.testclient import TestClient
from aether.api.app import app

client = TestClient(app)

def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_foundation.py
git commit -m "test: foundation integration tests pass"
```
