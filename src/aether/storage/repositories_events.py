import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, update, and_
from aether.storage.models_events import AgentEventModel

class AgentEventRepository:
    """
    Manages the persistence of events that trigger agent activity.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_event(self, event_id: str, agent_id: str, event_type: str, payload: dict, source: str, priority: int = 10, scheduled_at: float = None):
        stmt = insert(AgentEventModel).values(
            event_id=event_id,
            agent_id=agent_id,
            event_type=event_type,
            payload=json.dumps(payload),
            source=source,
            priority=priority,
            scheduled_at=scheduled_at
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_pending_events(self, now: float):
        """Retrieves events ready for processing based on their scheduled time."""
        stmt = select(AgentEventModel).where(
            (AgentEventModel.scheduled_at == None) |
            (AgentEventModel.scheduled_at <= now)
        ).order_by(AgentEventModel.priority.asc(), AgentEventModel.created_at.asc())
        result = await self.session.execute(stmt)
        events = result.scalars().all()

        # Return the model objects. Returning data transfer objects (DTOs) is preferred
        # to avoid SQLAlchemy autoflush issues when mutating model attributes.
        return events

    def deserialize_payload(self, event: AgentEventModel) -> dict:
        """Deserializes the payload of an event."""
        if isinstance(event.payload, str):
            return json.loads(event.payload)
        return event.payload

    async def delete_event(self, event_id: str):
        stmt = delete(AgentEventModel).where(AgentEventModel.event_id == event_id)
        await self.session.execute(stmt)
        await self.session.commit()
