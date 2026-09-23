import pytest
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository

@pytest.mark.asyncio
async def test_identity_lifecycle():
    await init_db()
    async with AsyncSessionLocal() as session:
        # Clean up
        from aether.storage.models import Identity
        from sqlalchemy import delete
        await session.execute(delete(Identity))
        await session.commit()

        repo = IdentityRepository(session)
        identity = await repo.create(
            agent_id="test_001",
            name="Aria",
            role="Researcher",
            personality={"trait": "analytical"},
            skills=["research"]
        )
        assert identity.name == "Aria"
        assert identity.role == "Researcher"
        assert identity.personality["trait"] == "analytical"
        assert "research" in identity.skills
