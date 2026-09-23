import pytest
import asyncio
from aether.agent.runtime import AgentRuntime
from aether.agent.lifecycle import AgentState
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.agent.identity import AgentIdentity

@pytest.mark.asyncio
async def test_runtime_state_transitions():
    await init_db()
    runtime = AgentRuntime()
    agent_id = "transition_test_001"

    # Setup agent in DB
    async with AsyncSessionLocal() as session:
        # Clean up to avoid IntegrityError
        from aether.storage.models import Agent, Identity
        from sqlalchemy import delete
        await session.execute(delete(Agent))
        await session.execute(delete(Identity))
        await session.commit()

        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "Test", "Role", {}, [])

    # 1. IDLE -> AWAKENED
    await runtime.wake(agent_id)
    assert runtime.active_agents[agent_id]["state"] == AgentState.AWAKENED

    # 2. AWAKENED -> THINKING (Simulated transition)
    # In the final implementation, the cognitive engine handles this,
    # but we can test if the runtime allows the state update.
    runtime.active_agents[agent_id]["state"] = AgentState.THINKING

    # 3. THINKING -> IDLE (Sleep)
    await runtime.sleep(agent_id)
    assert agent_id not in runtime.active_agents

    async with AsyncSessionLocal() as session:
        agent = await AgentRepository(session).get(agent_id)
        assert agent.status == AgentState.IDLE.name

@pytest.mark.asyncio
async def test_wake_non_existent_agent():
    runtime = AgentRuntime()
    with pytest.raises(ValueError, match=r"Agent .* not found"):
        await runtime.wake("ghost_agent")

@pytest.mark.asyncio
async def test_sleep_non_active_agent():
    runtime = AgentRuntime()
    # Should not raise exception
    await runtime.sleep("any_agent")
