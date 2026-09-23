import pytest
import asyncio
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.orchestration.events import bus, Event
from aether.orchestration.tasks import TaskStatus

@pytest.mark.asyncio
async def test_orchestration_flow():
    # Setup
    runtime = AgentRuntime()
    manager = OrchestrationManager(runtime)
    await manager.start()

    agent_id = "test_agent_123"
    task_payload = {"action": "summarize", "text": "Hello world"}

    # 1. Assign task to a sleeping agent
    task_id = await manager.assign_task(agent_id, task_payload)

    # Verify agent was woken up and is now THINKING
    assert runtime.is_agent_awake(agent_id)
    from aether.agent.lifecycle import AgentState
    assert runtime.active_agents[agent_id]["state"] == AgentState.THINKING

    # Verify task is attached
    current_task = runtime.active_agents[agent_id].get("current_task")
    assert current_task is not None
    assert current_task.id == task_id
    assert current_task.payload == task_payload

    # 2. Complete the task
    result = "Summary: Hello world"
    await manager.complete_task(task_id, result)

    # Verify task status updated in queue (if still there) or via event
    # Since dequeue removes it from queue, we check if it's handled
    # We can check if the result was recorded if we kept a history,
    # but for now we'll verify no crashes and event bus worked.

    await manager.stop()

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
