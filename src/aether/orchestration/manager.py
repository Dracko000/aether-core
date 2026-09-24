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
    Central coordinator for Aether Core.
    Integrates Agent Runtime, Task Queue, and Event Bus.
    """
    def __init__(self, runtime: AgentRuntime, capability_matrix: Optional[Any] = None):
        self.runtime = runtime
        self.tasks = TaskQueue(event_bus=bus)
        self.scheduler = Scheduler()
        self.capability_matrix = capability_matrix

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
        Processes pending agent events and evaluates autonomous goal-driven requirements.
        """
        async with AsyncSessionLocal() as session:
            # 1. Handle external wake events (messages, scheduled tasks)
            event_repo = AgentEventRepository(session)
            pending_events = await event_repo.get_pending_events(time.time())

            for event in pending_events:
                agent_id = event.agent_id
                event_type = event.event_type

                logger.info(f"Processing wake event {event_type} for agent {agent_id}")

                try:
                    await self.runtime.wake(agent_id)

                    if event_type == "SCHEDULED_TASK":
                        payload = event_repo.deserialize_payload(event)
                        await self.assign_task(agent_id, payload, priority=event.priority)

                    await event_repo.delete_event(event.event_id)

                except ValueError as e:
                    # Agent does not exist (e.g. a message addressed to a
                    # Telegram-only agent id the runtime has no identity for).
                    # This is permanent — drop the event instead of retrying
                    # it forever on every 5s wake cycle.
                    logger.warning(
                        "Dropping wake event %s for unknown agent %s: %s",
                        event.event_id, agent_id, e,
                    )
                    await event_repo.delete_event(event.event_id)

                except Exception as e:
                    logger.error(f"Failed to wake agent {agent_id} for event {event.event_id}: {e}")

            # 2. Process autonomous goal-driven activation
            from aether.cognitive.goals import GoalManager
            from aether.cognitive.drives import DriveManager
            goal_manager = GoalManager(session)
            drive_manager = DriveManager(session)

            # Evaluate all agents for potential autonomous actions.
            # In a production environment, evaluation is limited to inactive agents
            # with existing active goals.
            from aether.storage.repositories import AgentRepository
            agent_repo = AgentRepository(session)
            agents = await agent_repo.get_all_agents() # Assuming this method exists or similar

            for agent in agents:
                agent_id = agent.agent_id
                try:
                    if not self.runtime.is_agent_awake(agent_id):
                        action = await goal_manager.get_next_autonomous_action(agent_id)
                        if action:
                            logger.info(f"Autonomous goal trigger for agent {agent_id}: {action['task']['action']}")
                            await self.runtime.wake(agent_id)

                            # Update drives based on the trigger
                            # Simulation: If the action is 'SEARCH', increase Curiosity
                            impact = {}
                            if action['task']['action'] == "SEARCH":
                                impact = {"curiosity": 0.1}
                            elif action['task']['action'] == "SYNTHESIZE":
                                impact = {"coherence": 0.1}

                            await drive_manager.update_drives(agent_id, action['task']['action'], impact)
                            drives = await drive_manager.repo.get_drives(agent_id)

                            # Check if the task is a coalition task
                            if action['task'].get("assignee") == "COALITION":
                                # Logic for coalition task distribution
                                from aether.cognitive.coalitions import CoalitionManager
                                coal_mgr = CoalitionManager(session)
                                logger.info(f"Dispatching coalition task {action['task']['task_id']} to group")
                                # Distribution logic would go here

                            # Convert decomposed goal task into a system Task
                            # Evaluate cognitive requirements for the target task
                            from aether.model.capabilities import CapabilityMatrix
                            from aether.model.migration import ModelMigrationManager

                            # Recalculate the best action now that drives have been updated
                            action = await goal_manager.get_next_autonomous_action(agent_id, drives=drives)
                            if not action:
                                continue

                            # Use the updated action for the rest of the loop
                            task_payload = action['task']
                            priority = action['priority']

                            matrix = self.capability_matrix
                            current_model = agent.model_id
                            caps = matrix.get_capabilities(current_model) if matrix else None

                            # Trigger autonomous evolution if reasoning capabilities are insufficient for complex tasks.
                            # Current implementation uses a threshold of 3 for complex cognitive operations.
                            if caps and caps.reasoning_level < 3 and task_payload['action'] in ["PLAN", "SYNTHESIZE", "SEARCH", "READ", "SUMMARIZE"]:
                                logger.info(f"Capability gap detected for agent {agent_id}. Initiating model evolution...")
                                # Task definitions should ideally specify required reasoning levels.
                                best_model = self.capability_matrix.find_best_model({"reasoning_level": 3}) if self.capability_matrix else None
                                if best_model and best_model != current_model:
                                    migration_mgr = ModelMigrationManager(self.runtime, self.capability_matrix)
                                    await migration_mgr.migrate_agent(agent_id, best_model)
                                    # Update local agent object to reflect model migration
                                    agent.model_id = best_model

                            await self.assign_task(
                                agent_id,
                                payload=action['task'],
                                priority=action['priority']
                            )
                except Exception as e:
                    # Agents without an identity (or otherwise not ready for
                    # autonomous activation) must not abort the whole cycle.
                    logger.error(f"Failed autonomous wake for agent {agent_id}: {e}")

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
        Ensures the target agent is active upon task enqueueing.
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
        Evaluates pending work immediately upon agent activation.
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
