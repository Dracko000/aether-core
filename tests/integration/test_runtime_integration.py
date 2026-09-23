import pytest
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.agent.runtime import AgentRuntime
from aether.agent.lifecycle import AgentState

@pytest.mark.asyncio
async def test_runtime_integration_flow():
    await init_db()

    # Setup
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        agent_id = "integration_test_001"
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "Aria", "Researcher", {"trait": "analytical"}, ["research"])

    runtime = AgentRuntime()

    # 1. Wake Agent
    identity = await runtime.wake(agent_id)
    assert identity.name == "Aria"
    assert agent_id in runtime.active_agents

    # 2. Sleep Agent
    await runtime.sleep(agent_id)
    assert agent_id not in runtime.active_agents

    # 3. Verify Persistence
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get(agent_id)
        assert agent.status == AgentState.IDLE.name
