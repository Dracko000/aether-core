from aether.agent.lifecycle import AgentState, LifecycleManager
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.database import AsyncSessionLocal
from aether.agent.identity import AgentIdentity
from typing import Dict, Any, Optional
import logging
import uuid
from aether.storage.repositories_lifecycle import LifecycleRepository

logger = logging.getLogger("aether.agent.runtime")

class AgentRuntime:
    def __init__(self):
        self.active_agents: Dict[str, Dict[str, Any]] = {} # agent_id -> loaded_state

    async def _record_transition(self, session, agent_id: str, from_state: AgentState, to_state: AgentState, reason: str = None):
        """Persist state transition events to the lifecycle repository."""
        repo = LifecycleRepository(session)
        await repo.record_transition(
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            from_state=from_state.name,
            to_state=to_state.name,
            reason=reason
        )

    async def transition_to(self, session, agent_id: str, next_state: AgentState, reason: str = None):
        """
        Transition an agent to a new state after validating the move against the lifecycle matrix.
        """
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} is not active in runtime")

        current_state = self.active_agents[agent_id]["state"]

        if not LifecycleManager.validate_transition(current_state, next_state):
            logger.error(f"Invalid transition for {agent_id}: {current_state} -> {next_state}")
            return False

        # Update runtime state
        self.active_agents[agent_id]["state"] = next_state

        # Persist transition
        await self._record_transition(session, agent_id, current_state, next_state, reason)

        logger.info(f"Agent {agent_id} transitioned: {current_state.name} -> {next_state.name} ({reason})")
        return True

    async def wake(self, agent_id: str) -> AgentIdentity:
        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            id_repo = IdentityRepository(session)

            agent = await agent_repo.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            identity_data = await id_repo.get_by_id(agent_id)
            if not identity_data:
                raise ValueError(f"Identity for agent {agent_id} not found")

            identity = AgentIdentity(**identity_data)
            current_status = AgentState[agent.status] if agent.status in AgentState.__members__ else AgentState.IDLE

            # Transition to AWAKENED
            if LifecycleManager.validate_transition(current_status, AgentState.AWAKENED):
                agent.status = AgentState.AWAKENED.name
                await session.commit()
            else:
                # Initialize agent to IDLE before transitioning to AWAKENED if required
                if current_status == AgentState.CREATED:
                    agent.status = AgentState.IDLE.name
                    await session.commit()
                    agent.status = AgentState.AWAKENED.name
                    await session.commit()

            self.active_agents[agent_id] = {"identity": identity, "state": AgentState.AWAKENED}

            # Record the wake event
            await self._record_transition(session, agent_id, current_status, AgentState.AWAKENED, "runtime_wake")

            return identity

    async def sleep(self, agent_id: str):
        if agent_id not in self.active_agents:
            return

        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = await agent_repo.get(agent_id)

            current_state = self.active_agents[agent_id]["state"]

            if agent:
                # Ensure transition adheres to the lifecycle matrix
                if current_state == AgentState.IDLE:
                    agent.status = AgentState.SLEEPING.name
                    await session.commit()
                    await self._record_transition(session, agent_id, current_state, AgentState.SLEEPING, "manual_sleep")
                else:
                    # Standardize transition: move to IDLE before SLEEPING
                    await self.transition_to(session, agent_id, AgentState.IDLE, "preparing_for_sleep")
                    agent.status = AgentState.SLEEPING.name
                    await session.commit()
                    await self._record_transition(session, agent_id, AgentState.IDLE, AgentState.SLEEPING, "automatic_sleep")

        if agent_id in self.active_agents:
            del self.active_agents[agent_id]

    def is_agent_awake(self, agent_id: str) -> bool:
        """Verify if an agent is currently active in the runtime."""
        return agent_id in self.active_agents

    async def wake_agent(self, agent_id: str):
        """Initialize agent activation and emit the awakening event."""
        if agent_id not in self.active_agents:
            logger.info(f"Waking agent {agent_id}...")
            # Restore agent working memory from persistent storage
            self.active_agents[agent_id] = {"state": AgentState.AWAKENED, "context": {}}

            # Trigger event via the bus
            from aether.orchestration.events import bus, Event
            await bus.publish(Event(
                type="AGENT_AWAKENED",
                payload={"agent_id": agent_id}
            ))
        else:
            logger.debug(f"Agent {agent_id} is already awake")

    async def assign_immediate_task(self, agent_id: str, task: Any):
        """Assign a task directly to an active agent's execution context."""
        if agent_id in self.active_agents:
            # Session required for transition recording
            async with AsyncSessionLocal() as session:
                await self.transition_to(session, agent_id, AgentState.THINKING, f"task_assigned: {task.id}")
                self.active_agents[agent_id]["current_task"] = task
        else:
            logger.error(f"Cannot assign task to sleeping agent {agent_id}")
