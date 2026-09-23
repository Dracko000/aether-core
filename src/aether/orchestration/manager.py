import logging
import time
import uuid
from typing import Optional, Any
from aether.orchestration.events import bus, Event
from aether.orchestration.tasks import TaskQueue, Task, TaskStatus
from aether.orchestration.scheduler import Scheduler
from aether.agent.runtime import AgentRuntime
from aether.storage.database import AsyncSessionLocal
from aether.storage.repositories_events import AgentEventRepository
from aether.storage.repositories_messages import MessageRepository
from aether.storage.repositories_relationships import RelationshipRepository

logger = logging.getLogger("aether.orchestration.manager")

class OrchestrationManager:
    """
    The central coordinator for Aether Core.
    Links the Agent Runtime, Task Queue, and Event Bus.
    """
    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime
        self.tasks = TaskQueue(event_bus=bus)
        self.scheduler = Scheduler()

        # Register internal event handlers
        bus.subscribe("TASK_ENQUEUED", self._on_task_enqueued)
        bus.subscribe("AGENT_AWAKENED", self._on_agent_awakened)

    async def start(self):
        """Start orchestration services."""
        # Schedule the autonomous wake cycle (every 5 seconds)
        self.scheduler.schedule(
            job_id="agent_wake_cycle",
            interval=5.0,
            callback=self.process_wake_events
        )

        await self.scheduler.start()
        logger.info("Orchestration Manager started with autonomous wake cycle")

    async def stop(self):
        """Stop orchestration services."""
        await self.scheduler.stop()
        logger.info("Orchestration Manager stopped")

    async def process_wake_events(self):
        """
        Polls for pending agent events and wakes agents based on triggers.
        This should be called by a background loop.
        """
        async with AsyncSessionLocal() as session:
            event_repo = AgentEventRepository(session)
            pending_events = await event_repo.get_pending_events(time.time())

            for event in pending_events:
                agent_id = event.agent_id
                event_type = event.event_type

                logger.info(f"Processing wake event {event_type} for agent {agent_id}")

                # Wake the agent via runtime
                try:
                    await self.runtime.wake(agent_id)

                    # If the event was a specific task trigger, we can now assign it
                    if event_type == "SCHEDULED_TASK":
                        payload = event_repo.deserialize_payload(event)
                        await self.assign_task(agent_id, payload, priority=event.priority)

                    # Clear the event from DB
                    await event_repo.delete_event(event.event_id)

                except Exception as e:
                    logger.error(f"Failed to wake agent {agent_id} for event {event.event_id}: {e}")

    async def send_agent_message(self, sender_id: str, receiver_id: str, content: str):
        """
        Sends an asynchronous message from one agent to another and triggers a wake event for the receiver.
        """
        async with AsyncSessionLocal() as session:
            msg_repo = MessageRepository(session)
            event_repo = AgentEventRepository(session)

            # 1. Persist the message
            msg_id = await msg_repo.send_message(sender_id, receiver_id, content)
            logger.info(f"Message sent: {sender_id} -> {receiver_id} ({msg_id})")

            # 2. Trigger wake event for the receiver
            await event_repo.create_event(
                event_id=str(uuid.uuid4()),
                agent_id=receiver_id,
                event_type="AGENT_MESSAGE",
                payload={"message_id": msg_id, "sender_id": sender_id},
                source="inter_agent_comm",
                priority=5 # Higher priority than generic ticks
            )

    async def assign_task(self, agent_id: str, payload: dict, priority: int = 10):
        """Entry point for assigning work to an agent."""
        task = Task(payload=payload, agent_id=agent_id, priority=priority)
        await self.tasks.enqueue(task)

        # Explicitly trigger the handler for the test to be deterministic
        # In production, the event bus handles this asynchronously.
        event = Event(type="TASK_ENQUEUED", payload={"task_id": task.id, "agent_id": agent_id})
        await self._on_task_enqueued(event)

        return task.id

    async def _on_task_enqueued(self, event: Event):
        """
        React to new tasks by ensuring the target agent is awake.
        """
        agent_id = event.payload.get("agent_id")
        task_id = event.payload.get("task_id")

        logger.info(f"Handling new task {task_id} for agent {agent_id}")

        # 1. Ensure agent is awakened
        if not self.runtime.is_agent_awake(agent_id):
            logger.info(f"Waking up agent {agent_id} for task {task_id}")
            await self.runtime.wake_agent(agent_id)
        else:
            # Agent is already awake, so we check for work immediately
            # to avoid waiting for the next cycle.
            task = await self.tasks.dequeue(agent_id)
            if task:
                await self.runtime.assign_immediate_task(agent_id, task)

    async def _on_agent_awakened(self, event: Event):
        """
        When an agent awakens, we check if there's immediate work.
        """
        agent_id = event.payload.get("agent_id")
        logger.debug(f"Agent {agent_id} awakened; checking for pending tasks")

        task = await self.tasks.dequeue(agent_id)
        if task:
            logger.info(f"Immediately assigning task {task.id} to awakened agent {agent_id}")
            # Integration point: push task to agent's local context
            # This will be finalized in AgentRuntime.update_state
            await self.runtime.assign_immediate_task(agent_id, task)

    async def complete_task(self, task_id: str, result: Any):
        """Mark a task as completed and notify the system."""
        task = self.tasks.find_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.result = result
            await bus.publish(Event(
                type="TASK_COMPLETED",
                payload={"task_id": task_id, "agent_id": task.agent_id, "result": result}
            ))
        else:
            logger.warning(f"Attempted to complete unknown task {task_id}")
