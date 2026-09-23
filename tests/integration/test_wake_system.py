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
async def test_wake_event_flow():
    """Verify that scheduled events trigger agent activation and transition to cognitive processing."""
    agent_id = "wake_test_agent"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        await agent_repo.create(agent_id)
        await id_repo.create(
            agent_id=agent_id,
            name="Wake Agent",
            role="Tester",
            personality={},
            skills=[]
        )

        event_repo = AgentEventRepository(session)
        event_id = str(uuid.uuid4())
        await event_repo.create_event(
            event_id=event_id,
            agent_id=agent_id,
            event_type="SCHEDULED_TASK",
            payload={"task": "wake_up_and_do_this"},
            source="scheduler",
            priority=5
        )

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)

    # Process activation events
    await orch_manager.process_wake_events()

    # Verify agent activation in runtime
    assert runtime.is_agent_awake(agent_id)
    # Verify immediate transition to cognitive state for scheduled tasks
    assert runtime.active_agents[agent_id]["state"] == AgentState.THINKING

    # Verify task assignment
    assert "current_task" in runtime.active_agents[agent_id]
    assert runtime.active_agents[agent_id]["current_task"].payload == {"task": "wake_up_and_do_this"}

