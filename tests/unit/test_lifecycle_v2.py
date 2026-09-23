import pytest
import asyncio
from aether.agent.runtime import AgentRuntime
from aether.agent.lifecycle import AgentState
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_lifecycle import LifecycleRepository

@pytest.mark.asyncio
async def test_lifecycle_persistence():
    """
    Verify that state transitions are correctly persisted in the database.
    """
    agent_id = "lifecycle_test_agent"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        await agent_repo.create(agent_id)
        await id_repo.create(
            agent_id=agent_id,
            name="Lifecycle Agent",
            role="Tester",
            personality={},
            skills=[]
        )

    runtime = AgentRuntime()

    # 1. Transition from IDLE to AWAKENED
    await runtime.wake(agent_id)
    assert runtime.active_agents[agent_id]["state"] == AgentState.AWAKENED

    # 2. Transition to THINKING
    async with AsyncSessionLocal() as session:
        await runtime.transition_to(session, agent_id, AgentState.THINKING, "starting_reasoning")
        assert runtime.active_agents[agent_id]["state"] == AgentState.THINKING

        # 3. Verify persistence
        lifecycle_repo = LifecycleRepository(session)
        history = await lifecycle_repo.get_history(agent_id)

        # Verify record of state transitions
        assert len(history) >= 2
        assert history[-1].to_state == "THINKING"
        assert history[-1].reason == "starting_reasoning"

@pytest.mark.asyncio
async def test_invalid_transition():
    """
    Verify that prohibited state transitions are blocked.
    """
    agent_id = "invalid_trans_agent"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id)

        runtime = AgentRuntime()
        # Inject agent into active_agents for state validation testing
        runtime.active_agents[agent_id] = {"state": AgentState.CREATED}

        # CREATED -> THINKING is prohibited (requires INITIALIZED -> IDLE -> AWAKENED)
        success = await runtime.transition_to(session, agent_id, AgentState.THINKING, "illegal_jump")
        assert success is False
        assert runtime.active_agents[agent_id]["state"] == AgentState.CREATED

@pytest.mark.asyncio
async def test_sleep_lifecycle_flow():
    """
    Verify that the sleep operation updates the database and removes the agent from runtime.
    """
    agent_id = "sleep_test_agent"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id)

        runtime = AgentRuntime()
        runtime.active_agents[agent_id] = {"state": AgentState.IDLE}

        await runtime.sleep(agent_id)

        # Verify removal from active runtime
        assert agent_id not in runtime.active_agents

        # Verify persistence of SLEEPING status
        agent = await agent_repo.get(agent_id)
        assert agent.status == AgentState.SLEEPING.name
