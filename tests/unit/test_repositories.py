import pytest
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository

@pytest.mark.asyncio
async def test_agent_lifecycle():
    await init_db()
    async with AsyncSessionLocal() as session:
        repo = AgentRepository(session)
        agent = await repo.create("test_001")
        assert agent.agent_id == "test_001"

        fetched = await repo.get("test_001")
        assert fetched is not None
