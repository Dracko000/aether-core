from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from aether.storage.models import Base
from sqlalchemy import Table, Column, String, Text, Float, DateTime, MetaData
from datetime import datetime

metadata = MetaData()

# Episodic Memory Table
episodic_table = Table(
    "episodic_memories",
    metadata,
    Column("id", String, primary_key=True),
    Column("agent_id", String, index=True),
    Column("timestamp", DateTime, default=datetime.utcnow),
    Column("event", Text),
    Column("context", Text),
    Column("result", Text),
    Column("lesson", Text),
)

class EpisodicMemory:
    """
    L2 Episodic Memory: Log of raw experiences.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, agent_id: str, event: str, context: str, result: str, lesson: str = None):
        import uuid
        stmt = insert(episodic_table).values(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            event=event,
            context=context,
            result=result,
            lesson=lesson
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_recent(self, agent_id: str, limit: int = 10):
        stmt = select(episodic_table).where(episodic_table.c.agent_id == agent_id).order_by(episodic_table.c.timestamp.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.mappings().all()
