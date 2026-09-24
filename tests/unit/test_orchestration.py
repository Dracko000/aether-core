import pytest
import asyncio
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.orchestration.events import bus, Event
from aether.orchestration.tasks import TaskStatus

@pytest.mark.asyncio
async def test_orchestration_flow():
    from aether.storage.database import init_db
    # The full flow (wake -> task assign -> lifecycle transition) persists
    # lifecycle events, so the schema must exist before the manager starts.
    await init_db()

    # Initialize orchestration components
    runtime = AgentRuntime()
    manager = OrchestrationManager(runtime)
    await manager.start()

    agent_id = "test_agent_123"
    task_payload = {"action": "summarize", "text": "Hello world"}

    # 1. Task assignment to dormant agent
    task_id = await manager.assign_task(agent_id, task_payload)

    # Verify agent activation and state transition to THINKING
    assert runtime.is_agent_awake(agent_id)
    from aether.agent.lifecycle import AgentState
    assert runtime.active_agents[agent_id]["state"] == AgentState.THINKING

    # Verify task association
    current_task = runtime.active_agents[agent_id].get("current_task")
    assert current_task is not None
    assert current_task.id == task_id
    assert current_task.payload == task_payload

    # 2. Task completion
    result = "Summary: Hello world"
    await manager.complete_task(task_id, result)

    # Verify system stability and event bus functionality
    await manager.stop()

@pytest.mark.asyncio
async def test_drop_wake_event_for_unknown_agent():
    """Wake events for agents without an identity are dropped, not retried forever."""
    from aether.storage.database import init_db
    from aether.storage.database import AsyncSessionLocal
    from aether.storage.repositories_events import AgentEventRepository

    await init_db()

    runtime = AgentRuntime()
    manager = OrchestrationManager(runtime)

    async with AsyncSessionLocal() as session:
        repo = AgentEventRepository(session)
        event_id = "evt_ghost_agent"
        await repo.create_event(
            event_id=event_id,
            agent_id="ghost-agent",
            event_type="AGENT_MESSAGE",
            payload={"sender_id": "tester", "content": "hi"},
            source="test",
            scheduled_at=0,
        )

    await manager.process_wake_events()

    async with AsyncSessionLocal() as session:
        repo = AgentEventRepository(session)
        pending = await repo.get_pending_events(1e18)
        assert event_id not in {e.event_id for e in pending}
        assert not runtime.is_agent_awake("ghost-agent")


@pytest.mark.asyncio
async def test_scheduler_tick():
    from aether.orchestration.scheduler import Scheduler
    scheduler = Scheduler()

    tick_count = 0
    def increment():
        nonlocal tick_count
        tick_count += 1

    scheduler.schedule("tick_job", 0.05, increment)
    await scheduler.start()
    await asyncio.sleep(0.2)
    await scheduler.stop()

    assert tick_count >= 2

@pytest.mark.asyncio
async def test_event_bus_pubsub():
    received = []
    async def handler(event):
        received.append(event.payload["data"])

    bus.subscribe("TEST_EVENT", handler)
    await bus.publish(Event(type="TEST_EVENT", payload={"data": "hello"}))
    await bus.publish(Event(type="TEST_EVENT", payload={"data": "world"}))

    assert received == ["hello", "world"]
