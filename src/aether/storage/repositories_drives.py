from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from aether.storage.models_drives import AgentDriveModel
from typing import Dict, Optional

class DriveRepository:
    """
    Manages persistent storage and retrieval of agent cognitive drives.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_drives(self, agent_id: str) -> Optional[Dict[str, float]]:
        """Retrieves the current drive levels for a specific agent."""
        result = await self.session.execute(
            select(AgentDriveModel).where(AgentDriveModel.agent_id == agent_id)
        )
        drive_model = result.scalar_one_or_none()

        if drive_model:
            return {
                "curiosity": drive_model.curiosity,
                "coherence": drive_model.coherence,
                "stability": drive_model.stability,
            }
        return None

    async def update_drives(self, agent_id: str, drives: Dict[str, float]):
        """
        Updates drive levels for an agent. Creates a new record if one doesn't exist.
        """
        # Check if record exists
        existing = await self.get_drives(agent_id)

        if existing:
            # Update existing record
            stmt = (
                update(AgentDriveModel)
                .where(AgentDriveModel.agent_id == agent_id)
                .values(**drives)
            )
            await self.session.execute(stmt)
        else:
            # Create new record with provided values or defaults
            drive_model = AgentDriveModel(
                agent_id=agent_id,
                curiosity=drives.get("curiosity", 0.5),
                coherence=drives.get("coherence", 0.5),
                stability=drives.get("stability", 0.5)
            )
            self.session.add(drive_model)

        await self.session.commit()
