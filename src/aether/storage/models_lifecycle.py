from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from aether.storage.models import Base
from datetime import datetime

class LifecycleEvent(Base):
    """
    Immutable record of an agent's state transition.
    Provides the foundation for the Agent Timeline.
    """
    __tablename__ = "lifecycle_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    from_state: Mapped[str] = mapped_column(String)
    to_state: Mapped[str] = mapped_column(String)
    timestamp: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
    reason: Mapped[str] = mapped_column(Text, nullable=True)
