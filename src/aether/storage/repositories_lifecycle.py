from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from aether.storage.models_lifecycle import LifecycleEvent

class LifecycleRepository:
    """
    Manages the persistence of agent lifecycle state transitions.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_transition(self, event_id: str, agent_id: str, from_state: str, to_state: str, reason: str = None):
        stmt = insert(LifecycleEvent).values(
            event_id=event_id,
            agent_id=agent_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_history(self, agent_id: str):
        stmt = select(LifecycleEvent).where(LifecycleEvent.agent_id == agent_id).order_by(LifecycleEvent.timestamp.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
