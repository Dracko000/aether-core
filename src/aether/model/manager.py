import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Generic, TypeVar
from aether.model.adapter import ModelAdapter

T = TypeVar("T")

@dataclass(order=True)
class InferenceRequest(Generic[T]):
    priority: int
    # Using a lambda or closure to defer execution
    func: Callable[[], Awaitable[T]] = field(compare=False)
    future: asyncio.Future = field(compare=False)

class ModelManager:
    """
    Coordinates access to the model backend.
    Serializes inference requests to maintain stability within constrained
    memory environments (e.g., 8GB RAM).
    """
    def __init__(self, adapter: ModelAdapter):
        self.adapter = adapter
        self.queue = asyncio.PriorityQueue()
        # Start background worker
        self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            request = await self.queue.get()
            try:
                # Execute adapter call
                result = await request.func()
                request.future.set_result(result)
            except Exception as e:
                request.future.set_exception(e)
            finally:
                self.queue.task_done()

    async def request(self, priority: int, func: Callable[[], Awaitable[T]]) -> T:
        """
        Submits a model request to the priority queue.
        :param priority: Priority level (lower values indicate higher priority).
        :param func: Awaitable function executing the adapter call.
        """
        future = asyncio.get_event_loop().create_future()
        await self.queue.put(InferenceRequest(priority, func, future))
        return await future

    async def shutdown(self):
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
