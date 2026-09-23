import pytest
import asyncio
from aether.model.manager import ModelManager
from aether.model.mock import MockAdapter

@pytest.mark.asyncio
async def test_priority_execution():
    # Initialize ModelManager with mock adapter
    adapter = MockAdapter()
    manager = ModelManager(adapter)

    results = []
    async def task(name, sleep_time):
        await asyncio.sleep(sleep_time)
        results.append(name)
        return name

    # Submit tasks with varying priority levels (1 = High, 10 = Low)
    t1 = asyncio.create_task(manager.request(10, lambda: task("low", 0.01)))
    t2 = asyncio.create_task(manager.request(1, lambda: task("high", 0.01)))

    await asyncio.gather(t1, t2)

    # Verify that high-priority tasks are dispatched first
    assert results[0] == "high"
    assert results[1] == "low"

    await manager.shutdown()
