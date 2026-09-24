from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, ForeignKey
from aether.storage.models import Base
from datetime import datetime, timezone
from typing import Optional

class AgentEventModel(Base):
    """
    Persistent storage for events that trigger agent activity.
    """
    __tablename__ = "agent_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    priority: Mapped[int] = mapped_column(default=10)
    payload: Mapped[dict] = mapped_column(Text) # Store as JSON string or JSON type
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
    scheduled_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
