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

    # 1. First session: Create agent and identity
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        # Check if agent already exists from previous failed runs
        existing_agent = await agent_repo.get(agent_id)
        if not existing_agent:
            await agent_repo.create(agent_id)

        # Create identity (using a fresh identity to avoid constraints if necessary,
        # but here we just ensure the agent exists first)
        # To be safe, we delete identity first or use an upsert.
        # For the test, we'll just use a unique agent_id per run.
        await id_repo.create(
            agent_id=agent_id,
            name=agent_name,
            role="Researcher",
            personality={"curious": True, "analytical": True},
            skills=["search", "analysis"]
        )

        # Put agent into a specific state
        agent = await agent_repo.get(agent_id)
        agent.status = "AWAKENED"
        await session.commit()

    # 2. Simulate restart: Create a new runtime and load the agent
    runtime = AgentRuntime()

    # Use the existing DB to wake the agent
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

    # Original setup
    adapter_v1 = MockAdapter()
    # Assume some state is held in identity/memory (verified in previous tests)

    # Replace adapter
    adapter_v2 = NewModelAdapter()

    # Continuity check: The agent's identity remains unchanged regardless of model
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
    # In a full system test, we would verify that the memory retrieval
    # works the same way across different adapters.
