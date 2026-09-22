import pytest
import os
from aether.storage.database import AsyncSessionLocal, init_db, engine
from aether.storage.repositories import AgentRepository, IdentityRepository

@pytest.mark.asyncio
async def test_agent_lifecycle():
    # Ensure we start with a clean DB for the test
    # In a real project, we'd use a separate test DB file
    await init_db()

    async with AsyncSessionLocal() as session:
        # Clear the table first to avoid IntegrityError
        from aether.storage.models import Agent
        from sqlalchemy import delete
        await session.execute(delete(Agent))
        await session.commit()

        repo = AgentRepository(session)
        agent = await repo.create("test_001")
        assert agent.agent_id == "test_001"

        fetched = await repo.get("test_001")
        assert fetched is not None
