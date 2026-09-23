import pytest
import asyncio
import uuid
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_relationships import RelationshipRepository
from aether.storage.repositories_messages import MessageRepository

@pytest.mark.asyncio
async def test_social_lifecycle():
    agent_a = "agent_a"
    agent_b = "agent_b"
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        rel_repo = RelationshipRepository(session)
        msg_repo = MessageRepository(session)
        
        await agent_repo.create(agent_a)
        await agent_repo.create(agent_b)
        
        # 1. Set relationship
        await rel_repo.set_relationship(agent_a, agent_b, rel_type="ALLY", trust=0.9, notes="Trusted partner")
        rel = await rel_repo.get_relationship(agent_a, agent_b)
        assert rel is not None
        assert rel.relationship_type == "ALLY"
        assert rel.trust_score == 0.9
        
        # 2. Send message
        msg_id = await msg_repo.send_message(agent_a, agent_b, "Hello Agent B!")
        assert msg_id is not None
        
        # 3. Get unread messages for B
        unread = await msg_repo.get_unread_messages(agent_b)
        assert len(unread) == 1
        assert unread[0].sender_id == agent_a
        assert unread[0].content == "Hello Agent B!"
        
        # 4. Mark as read
        await msg_repo.mark_as_read(msg_id)
        unread_after = await msg_repo.get_unread_messages(agent_b)
        assert len(unread_after) == 0

