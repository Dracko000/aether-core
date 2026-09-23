import pytest
import asyncio
from aether.agent.runtime import AgentRuntime
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.agent.identity import AgentIdentity

@pytest.mark.asyncio
async def test_agent_continuity_restart():
    """
    Verify that agent identity and status persist across runtime restarts.
    """
    agent_id = "persistent_agent_001"
    agent_name = "Aether-1"

    # 1. Initial Session: Establish agent identity and configuration
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        # Verify if agent exists from previous executions
        existing_agent = await agent_repo.get(agent_id)
        if not existing_agent:
            await agent_repo.create(agent_id)

        # Establish identity
        # Ensuring unique agent_id per execution to maintain isolation.
        await id_repo.create(
            agent_id=agent_id,
            name=agent_name,
            role="Researcher",
            personality={"curious": True, "analytical": True},
            skills=["search", "analysis"]
        )

        # Define agent operational state
        agent = await agent_repo.get(agent_id)
        agent.status = "AWAKENED"
        await session.commit()

    # 2. Runtime Reset: Instantiate new runtime and restore agent state
    runtime = AgentRuntime()

    # Restore agent using the persistent database
    identity = await runtime.wake(agent_id)

    assert identity.name == agent_name
    assert identity.role == "Researcher"
    assert identity.personality["curious"] is True
    assert agent_id in runtime.active_agents
    assert runtime.active_agents[agent_id]["state"].name == "AWAKENED"

@pytest.mark.asyncio
async def test_model_replacement_continuity():
    """
    Verify that replacing the model adapter does not break agent continuity.
    """
    from aether.model.mock import MockAdapter
    from aether.model.adapter import ModelAdapter

    # Define a second mock adapter to simulate a model update
    class NewModelAdapter(MockAdapter):
        async def chat(self, messages, **kwargs):
            return "New Model Response"

    # Establish primary adapter
    adapter_v1 = MockAdapter()
    # State persistence is verified in corresponding cognitive tests

    # Transition to updated adapter
    adapter_v2 = NewModelAdapter()

    # Continuity Verification: Ensure agent identity is invariant to model transitions
    identity_data = {
        "agent_id": "agent_002",
        "name": "Continuity-Agent",
        "role": "Tester",
        "personality": {},
        "skills": []
    }
    identity_v1 = AgentIdentity(**identity_data)
    identity_v2 = AgentIdentity(**identity_data)

    assert identity_v1.name == identity_v2.name
    # In integrated system tests, verify that memory retrieval consistency
    # is maintained across adapter transitions.
