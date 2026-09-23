import pytest
import asyncio
import uuid
import time
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_events import AgentEventRepository
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.agent.lifecycle import AgentState

@pytest.mark.asyncio
async def test_autonomous_wake_loop():
    agent_id = "auto_wake_agent"
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        
        await agent_repo.create(agent_id)
        await id_repo.create(
            agent_id=agent_id,
            name="Auto Agent",
            role="Tester",
            personality={},
            skills=[]
        )
        
        event_repo = AgentEventRepository(session)
        await event_repo.create_event(
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            event_type="USER_MESSAGE",
            payload={"text": "Wake up!"},
            source="api"
        )

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)
    
    # Start the manager (this schedules the wake cycle)
    await orch_manager.start()
    
    # Wait for the scheduler to tick at least once
    # The interval is 5s, so we wait slightly more.
    # To speed up tests, we could modify the interval, but let's verify real behavior.
    # Since we are in a test, we can manually trigger if we want, 
    # but the goal is to test the scheduler.
    
    # Instead of waiting 5s, we can manually invoke the callback for the test 
    # or just wait a bit. Let's wait 6s to be sure.
    await asyncio.sleep(6)
    
    # Verify agent was woken up by the scheduler
    assert runtime.is_agent_awake(agent_id)
    
    await orch_manager.stop()

