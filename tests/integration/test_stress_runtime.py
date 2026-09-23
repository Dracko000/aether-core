import pytest
import asyncio
import uuid
import time
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager

@pytest.mark.asyncio
async def test_runtime_load():
    """
    Stress test: Wake up a large number of agents to check for memory leaks or OOM.
    """
    num_agents = 100
    agent_ids = [f"stress_agent_{i}" for i in range(num_agents)]
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        
        for aid in agent_ids:
            await agent_repo.create(aid)
            await id_repo.create(aid, f"Agent {aid}", "Worker", {}, [])

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)
    
    start_time = time.time()
    
    # Wake up all agents concurrently
    tasks = [runtime.wake(aid) for aid in agent_ids]
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    assert len(runtime.active_agents) == num_agents
    print(f"\nWoke up {num_agents} agents in {end_time - start_time:.2f} seconds")

@pytest.mark.asyncio
async def test_event_flood():
    """
    Stress test: Flood the system with events to check for queue congestion.
    """
    agent_id = "flood_agent"
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "Flood Agent", "Receiver", {}, [])

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)
    
    # Flood with 500 events
    async with AsyncSessionLocal() as session:
        from aether.storage.repositories_events import AgentEventRepository
        event_repo = AgentEventRepository(session)
        for i in range(500):
            await event_repo.create_event(
                event_id=str(uuid.uuid4()),
                agent_id=agent_id,
                event_type="TICKER",
                payload={"tick": i},
                source="stress_test"
            )
    
    start_time = time.time()
    await orch_manager.process_wake_events()
    end_time = time.time()
    
    print(f"\nProcessed 500 events in {end_time - start_time:.2f} seconds")
    assert runtime.is_agent_awake(agent_id)

