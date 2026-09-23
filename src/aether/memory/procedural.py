from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Table, Column, String, Text, MetaData
from sqlalchemy import select, insert

metadata = MetaData()

procedural_table = Table(
    "procedural_memories",
    metadata,
    Column("id", String, primary_key=True),
    Column("agent_id", String, index=True),
    Column("task", String),
    Column("procedure", Text),
)

class ProceduralMemory:
    """
    L4 Procedural Memory: Knowledge about how to perform tasks.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, agent_id: str, task: str, procedure: str):
        import uuid
        stmt = insert(procedural_table).values(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            task=task,
            procedure=procedure
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_procedure(self, agent_id: str, task: str):
        stmt = select(procedural_table).where(procedural_table.c.agent_id == agent_id, procedural_table.c.task == task)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
