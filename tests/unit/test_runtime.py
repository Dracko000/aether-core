import pytest
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.agent.runtime import AgentRuntime
from aether.agent.lifecycle import AgentState

@pytest.mark.asyncio
async def test_runtime_wake_sleep():
    await init_db()

    # Agent instantiation in database
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        agent_id = "runtime_test_001"

        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "TestBot", "Tester", {"trait": "analytical"}, ["test_skill"])

    runtime = AgentRuntime()

    # 1. Activate agent
    identity = await runtime.wake("runtime_test_001")
    assert identity.name == "TestBot"
    assert "runtime_test_001" in runtime.active_agents
    assert runtime.active_agents["runtime_test_001"]["state"] == AgentState.AWAKENED

    # 2. Deactivate agent
    await runtime.sleep("runtime_test_001")
    assert "runtime_test_001" not in runtime.active_agents

    # 3. Verify persistence of IDLE state
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get("runtime_test_001")
        assert agent.status == AgentState.IDLE.name
