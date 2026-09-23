from aether.agent.lifecycle import AgentState, LifecycleManager
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.database import AsyncSessionLocal
from aether.agent.identity import AgentIdentity
from typing import Dict, Any

class AgentRuntime:
    def __init__(self):
        self.active_agents: Dict[str, Dict[str, Any]] = {} # agent_id -> loaded_state

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

            # Transition: IDLE -> AWAKENED
            # We map the DB string status back to the Enum
            current_status = AgentState[agent.status] if agent.status in AgentState.__members__ else AgentState.IDLE

            if LifecycleManager.validate_transition(current_status, AgentState.AWAKENED):
                agent.status = AgentState.AWAKENED.name
                await session.commit()

            self.active_agents[agent_id] = {"identity": identity, "state": AgentState.AWAKENED}
            return identity

    async def sleep(self, agent_id: str):
        if agent_id not in self.active_agents:
            return

        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = await agent_repo.get(agent_id)

            if agent:
                # Transition: ... -> IDLE
                agent.status = AgentState.IDLE.name
                await session.commit()

        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
