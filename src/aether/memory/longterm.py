from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from aether.storage.models import LongTermMemory

class LongTermMemoryManager:
    """
    L5 Long-Term Memory: Core identity and highly distilled insights.
    Now uses the centralized SQLAlchemy model.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, agent_id: str, fact: str, importance: float):
        from datetime import datetime
        # Create a LongTermMemory object
        memory = LongTermMemory(
            agent_id=agent_id,
            fact=fact,
            importance=importance,
            timestamp=datetime.utcnow().timestamp()
        )
        self.session.add(memory)
        await self.session.commit()

    async def get_core_insights(self, agent_id: str):
        # Using SQLAlchemy select
        from sqlalchemy import select
        stmt = select(LongTermMemory).where(LongTermMemory.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
