from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
import uuid
import asyncio
import logging

logger = logging.getLogger("aether.orchestration.tasks")

class TaskStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """Represents a discrete unit of work for an agent."""
    payload: Dict[str, Any]
    agent_id: str
    priority: int = 10  # Lower is higher priority
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            try:
                self.created_at = asyncio.get_running_loop().time()
            except RuntimeError:
                self.created_at = 0.0

class TaskQueue:
    """
    Manages a prioritized queue of tasks.
    Integrated with the event bus to notify the system when tasks arrive.
    """
    def __init__(self, event_bus=None):
        self._queue: List[Task] = []
        self._bus = event_bus

    async def enqueue(self, task: Task):
        """Add a task to the queue and sort by priority."""
        self._queue.append(task)
        self._queue.sort(key=lambda t: t.priority)

        logger.debug(f"Task {task.id} enqueued for agent {task.agent_id}")

        if self._bus:
            from aether.orchestration.events import Event
            await self._bus.publish(Event(
                type="TASK_ENQUEUED",
                payload={"task_id": task.id, "agent_id": task.agent_id}
            ))

    async def dequeue(self, agent_id: Optional[str] = None) -> Optional[Task]:
        """Get the highest priority task, optionally filtered by agent."""
        for i, task in enumerate(self._queue):
            if agent_id is None or task.agent_id == agent_id:
                return self._queue.pop(i)
        return None

    def get_status(self) -> Dict[str, int]:
        """Return counts of tasks by status."""
        stats = {status.value: 0 for status in TaskStatus}
        for t in self._queue:
            stats[t.status.value] += 1
        return stats

    def find_task(self, task_id: str) -> Optional[Task]:
        """Find a task by its ID."""
        return next((t for t in self._queue if t.id == task_id), None)
