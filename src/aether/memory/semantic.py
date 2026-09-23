from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Table, Column, String, Text, Float, MetaData
from sqlalchemy import select, insert

metadata = MetaData()

semantic_table = Table(
    "semantic_memories",
    metadata,
    Column("id", String, primary_key=True),
    Column("agent_id", String, index=True),
    Column("fact", Text),
    Column("importance", Float),
)

class SemanticMemory:
    """
    L3 Semantic Memory: Persistent facts and concepts.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, agent_id: str, fact: str, importance: float):
        import uuid
        stmt = insert(semantic_table).values(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            fact=fact,
            importance=importance
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_facts(self, agent_id: str, min_importance: float = 0.0):
        stmt = select(semantic_table).where(semantic_table.c.agent_id == agent_id, semantic_table.c.importance >= min_importance)
        result = await self.session.execute(stmt)
        return result.mappings().all()
