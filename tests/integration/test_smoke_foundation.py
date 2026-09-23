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
    # 1. Setup
    await init_db()

    # Clear DB to ensure clean state
    async with AsyncSessionLocal() as session:
        from aether.storage.models import Agent, Identity
        from sqlalchemy import delete
        await session.execute(delete(Agent))
        await session.execute(delete(Identity))
        await session.commit()

    mock_adapter = MockAdapter()
    manager = ModelManager(mock_adapter)

    # 2. Create Agent via API
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

    # 3. Simulate a Cognitive Request (Runtime -> Manager -> Adapter)
    # We want the agent to "Plan" something
    async def plan_call():
        # Simulate what the Cognitive Engine would do:
        return await mock_adapter.structured([], PlanSchema)

    result = await manager.request(1, plan_call)

    # Verify structured output
    assert isinstance(result, PlanSchema)
    # MockAdapter returns "mock_value" for all strings
    assert result.steps == ["mock_value"] # Based on MockAdapter implementation

    await manager.shutdown()

@pytest.mark.asyncio
async def test_priority_queue_stress():
    adapter = MockAdapter()
    manager = ModelManager(adapter)

    processed_order = []
    async def slow_task(name):
        await asyncio.sleep(0.01)
        processed_order.append(name)
        return name

    # Submit in reverse order of priority
    # Prio 10 (Low), Prio 5 (Med), Prio 1 (High)
    t1 = asyncio.create_task(manager.request(10, lambda: slow_task("low")))
    t2 = asyncio.create_task(manager.request(5, lambda: slow_task("med")))
    t3 = asyncio.create_task(manager.request(1, lambda: slow_task("high")))

    await asyncio.gather(t1, t2, t3)

    # Should be high -> med -> low
    assert processed_order == ["high", "med", "low"]
    await manager.shutdown()
