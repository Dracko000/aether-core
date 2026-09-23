import pytest
import asyncio
import uuid
import time
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_events import AgentEventRepository

@pytest.mark.asyncio
async def test_event_lifecycle():
    agent_id = "event_test_agent"
    event_id = str(uuid.uuid4())
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        event_repo = AgentEventRepository(session)
        
        # Need agent to exist due to ForeignKey
        await agent_repo.create(agent_id)
        
        # 1. Create immediate event
        await event_repo.create_event(
            event_id=event_id,
            agent_id=agent_id,
            event_type="USER_MESSAGE",
            payload={"text": "hello"},
            source="api"
        )
        
        # 2. Create scheduled event (future)
        future_id = str(uuid.uuid4())
        await event_repo.create_event(
            event_id=future_id,
            agent_id=agent_id,
            event_type="TICKER",
            payload={},
            source="scheduler",
            scheduled_at=time.time() + 100
        )
        
        # 3. Get pending (only immediate should appear)
        pending = await event_repo.get_pending_events(time.time())
        assert len(pending) == 1
        assert pending[0].event_id == event_id
        
        # Verify payload deserialization
        payload = event_repo.deserialize_payload(pending[0])
        assert payload == {"text": "hello"}
        
        # 4. Delete event
        await event_repo.delete_event(event_id)
        pending_after = await event_repo.get_pending_events(time.time())
        assert len(pending_after) == 0

