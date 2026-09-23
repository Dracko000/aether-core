import pytest
import asyncio
import uuid
import time
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_events import AgentEventRepository
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.agent.lifecycle import AgentState

@pytest.mark.asyncio
async def test_autonomous_wake_loop():
    """Verify the autonomous activation loop correctly processes pending events via the scheduler."""
    agent_id = "auto_wake_agent"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        await agent_repo.create(agent_id)
        await id_repo.create(
            agent_id=agent_id,
            name="Auto Agent",
            role="Tester",
            personality={},
            skills=[]
        )

        event_repo = AgentEventRepository(session)
        await event_repo.create_event(
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            event_type="USER_MESSAGE",
            payload={"text": "Wake up!"},
            source="api"
        )

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)

    # Initialize the orchestration manager to schedule the wake cycle
    await orch_manager.start()

    # Wait for the scheduler to execute its periodic tick
    await asyncio.sleep(6)

    # Verify agent activation via scheduler
    assert runtime.is_agent_awake(agent_id)

    await orch_manager.stop()

