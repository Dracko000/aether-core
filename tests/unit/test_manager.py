import pytest
import asyncio
from aether.model.manager import ModelManager
from aether.model.mock import MockAdapter

@pytest.mark.asyncio
async def test_priority_execution():
    # Setup
    adapter = MockAdapter()
    manager = ModelManager(adapter)

    results = []
    async def task(name, sleep_time):
        await asyncio.sleep(sleep_time)
        results.append(name)
        return name

    # Submit low priority (10) then high priority (1)
    # We launch them as tasks so they are submitted nearly simultaneously
    t1 = asyncio.create_task(manager.request(10, lambda: task("low", 0.01)))
    t2 = asyncio.create_task(manager.request(1, lambda: task("high", 0.01)))

    await asyncio.gather(t1, t2)

    # In a strict priority queue, "high" should have been picked first
    # as soon as the worker was free.
    assert results[0] == "high"
    assert results[1] == "low"

    await manager.shutdown()
