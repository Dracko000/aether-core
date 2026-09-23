from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Table, Column, String, Text, Float, MetaData
from sqlalchemy import select, insert

metadata = MetaData()

longterm_table = Table(
    "longterm_memories",
    metadata,
    Column("id", String, primary_key=True),
    Column("agent_id", String, index=True),
    Column("insight", Text),
    Column("weight", Float),
)

class LongTermMemory:
    """
    L5 Long-Term Memory: Core identity and highly distilled insights.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, agent_id: str, insight: str, weight: float):
        import uuid
        stmt = insert(longterm_table).values(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            insight=insight,
            weight=weight
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_core_insights(self, agent_id: str):
        stmt = select(longterm_table).where(longterm_table.c.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return result.mappings().all()
