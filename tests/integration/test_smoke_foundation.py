import pytest
import asyncio
from fastapi.testclient import TestClient
from aether.api.app import app
from aether.storage.database import init_db, AsyncSessionLocal
from aether.model.manager import ModelManager
from aether.model.mock import MockAdapter
from aether.storage.repositories import AgentRepository, IdentityRepository
from pydantic import BaseModel

class PlanSchema(BaseModel):
    steps: list[str]

@pytest.mark.asyncio
async def test_full_stack_mock_flow():
    """Verify end-to-end flow from API agent creation to cognitive request processing using mock adapters."""
    # 1. Environment Setup
    await init_db()

    # Ensure clean state
    async with AsyncSessionLocal() as session:
        from aether.storage.models import Agent, Identity
        from sqlalchemy import delete
        await session.execute(delete(Agent))
        await session.execute(delete(Identity))
        await session.commit()

    mock_adapter = MockAdapter()
    manager = ModelManager(mock_adapter)

    # 2. Agent Provisioning via API
    client = TestClient(app)
    agent_payload = {
        "agent_id": "aria_test",
        "name": "Aria",
        "role": "Researcher",
        "personality": {"trait": "analytical"},
        "skills": ["research"]
    }
    response = client.post("/agents/", json=agent_payload)
    assert response.status_code == 200

    # 3. Cognitive Request Simulation
    async def plan_call():
        # Simulate cognitive engine's request for structured planning
        return await mock_adapter.structured([], PlanSchema)

    result = await manager.request(1, plan_call)

    # Verify structured output validity
    assert isinstance(result, PlanSchema)
    assert result.steps == ["mock_value"] # Verified against MockAdapter implementation

    await manager.shutdown()

@pytest.mark.asyncio
async def test_priority_queue_stress():
    """Verify that the ModelManager processes requests according to assigned priority."""
    adapter = MockAdapter()
    manager = ModelManager(adapter)

    processed_order = []
    async def slow_task(name):
        await asyncio.sleep(0.01)
        processed_order.append(name)
        return name

    # Submit requests in reverse priority order: Low (10), Medium (5), High (1)
    t1 = asyncio.create_task(manager.request(10, lambda: slow_task("low")))
    t2 = asyncio.create_task(manager.request(5, lambda: slow_task("med")))
    t3 = asyncio.create_task(manager.request(1, lambda: slow_task("high")))

    await asyncio.gather(t1, t2, t3)

    # Verify priority-based execution order
    assert processed_order == ["high", "med", "low"]
    await manager.shutdown()
