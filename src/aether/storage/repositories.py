from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aether.storage.models import Agent, Identity
from typing import Optional

class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, agent_id: str):
        agent = Agent(agent_id=agent_id)
        self.session.add(agent)
        await self.session.commit()
        return agent

    async def get(self, agent_id: str):
        result = await self.session.execute(select(Agent).where(Agent.agent_id == agent_id))
        return result.scalar_one_or_none()

class IdentityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, agent_id: str, name: str, role: str, personality: dict, skills: list):
        identity = Identity(agent_id=agent_id, name=name, role=role, personality=personality, skills=skills)
        self.session.add(identity)
        await self.session.commit()
        return identity

    async def get_by_id(self, agent_id: str) -> Optional[dict]:
        result = await self.session.execute(select(Identity).where(Identity.agent_id == agent_id))
        identity = result.scalar_one_or_none()
        if identity:
            return {
                "agent_id": identity.agent_id,
                "name": identity.name,
                "role": identity.role,
                "personality": identity.personality,
                "skills": identity.skills,
            }
        return None
