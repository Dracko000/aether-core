from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aether.storage.models import EpisodicMemory

class EpisodicMemoryManager:
    """
    L2 Episodic Memory: Maintains a chronological log of raw experiences
    via a centralized SQLAlchemy model.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, agent_id: str, event: str, context: str, result: str, lesson: str = None):
        from datetime import datetime
        # Persist episodic record
        memory = EpisodicMemory(
            agent_id=agent_id,
            timestamp=datetime.utcnow().timestamp(),
            event=event,
            context=context,
            result=result,
            lesson=lesson
        )
        self.session.add(memory)
        await self.session.commit()

    async def get_recent(self, agent_id: str, limit: int = 10):
        from sqlalchemy import select
        stmt = select(EpisodicMemory).where(EpisodicMemory.agent_id == agent_id).order_by(EpisodicMemory.timestamp.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
