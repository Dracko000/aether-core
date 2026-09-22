from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aether.storage.models import Agent, Identity

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
