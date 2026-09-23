import pytest
import asyncio
import uuid
import time
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.agent.lifecycle import AgentState

@pytest.mark.asyncio
async def test_messaging_wake_flow():
    """Verify that receiving a message triggers agent activation."""
    agent_a = "agent_a"
    agent_b = "agent_b"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        await agent_repo.create(agent_a)
        await id_repo.create(agent_id=agent_a, name="Agent A", role="Sender", personality={}, skills=[])

        await agent_repo.create(agent_b)
        await id_repo.create(agent_id=agent_b, name="Agent B", role="Receiver", personality={}, skills=[])

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)

    # Agent A initiates communication with Agent B
    await orch_manager.send_agent_message(agent_a, agent_b, "Hello from A!")

    # Process activation events
    await orch_manager.process_wake_events()

    # Verify Agent B activation
    assert runtime.is_agent_awake(agent_b)
    assert runtime.active_agents[agent_b]["state"] == AgentState.AWAKENED
