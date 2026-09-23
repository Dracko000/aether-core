from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete
from aether.storage.models_evolution import AgentMigrationModel
from typing import List

class EvolutionRepository:
    """
    Manages the persistence of model migration history.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_migration(self, migration_id: str, agent_id: str, from_model: str, to_model: str, status: str = "SUCCESS", notes: str = None):
        """Records a model migration event."""
        stmt = insert(AgentMigrationModel).values(
            migration_id=migration_id,
            agent_id=agent_id,
            from_model_id=from_model,
            to_model_id=to_model,
            status=status,
            notes=notes
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_migration_history(self, agent_id: str) -> List[AgentMigrationModel]:
        """Retrieves the migration history for a specific agent."""
        stmt = select(AgentMigrationModel).where(
            AgentMigrationModel.agent_id == agent_id
        ).order_by(AgentMigrationModel.timestamp.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
