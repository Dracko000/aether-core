from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from aether.storage.models_drives import AgentDriveModel
from typing import Dict, Optional

class DriveState(dict):
    """
    A dict of drive/emotion levels that also exposes each key as an attribute
    (``drives["curiosity"]`` and ``drives.curiosity`` both work). Used so the
    rest of the codebase can treat drives as a mapping while tests may access
    individual fields as attributes.
    """
    def __getattr__(self, name: str) -> float:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

class DriveRepository:
    """
    Manages persistent storage and retrieval of agent cognitive drives.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_drives(self, agent_id: str) -> Optional[Dict[str, float]]:
        """Retrieves the current drive levels and emotional state for a specific agent."""
        result = await self.session.execute(
            select(AgentDriveModel).where(AgentDriveModel.agent_id == agent_id)
        )
        drive_model = result.scalar_one_or_none()

        if drive_model:
            return DriveState(
                curiosity=drive_model.curiosity,
                coherence=drive_model.coherence,
                stability=drive_model.stability,
                frustration=drive_model.frustration,
                satisfaction=drive_model.satisfaction,
                anxiety=drive_model.anxiety,
                joy=drive_model.joy,
            )
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
                stability=drives.get("stability", 0.5),
                frustration=drives.get("frustration", 0.0),
                satisfaction=drives.get("satisfaction", 0.0),
                anxiety=drives.get("anxiety", 0.0),
                joy=drives.get("joy", 0.0),
            )
            self.session.add(drive_model)

        await self.session.commit()