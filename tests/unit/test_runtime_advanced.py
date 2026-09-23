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

    # Agent instantiation in database
    async with AsyncSessionLocal() as session:
        # Prevent IntegrityError by clearing existing records
        from aether.storage.models import Agent, Identity
        from sqlalchemy import delete
        await session.execute(delete(Agent))
        await session.execute(delete(Identity))
        await session.commit()

        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "Test", "Role", {}, [])

    # 1. Transition: IDLE -> AWAKENED
    await runtime.wake(agent_id)
    assert runtime.active_agents[agent_id]["state"] == AgentState.AWAKENED

    # 2. Transition: AWAKENED -> THINKING
    # The cognitive engine manages this in production; here we verify runtime state update.
    runtime.active_agents[agent_id]["state"] = AgentState.THINKING

    # 3. Transition: THINKING -> IDLE (Sleep)
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
    # Verify that sleeping a non-active agent does not raise an exception
    await runtime.sleep("any_agent")
