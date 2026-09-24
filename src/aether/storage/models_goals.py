from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, ForeignKey, Boolean
from aether.storage.models import Base
from datetime import datetime, timezone

class AgentGoalModel(Base):
    """
    Persistent storage for agent goals and objectives.
    """
    __tablename__ = "agent_goals"

    goal_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(default=10)
    status: Mapped[str] = mapped_column(String, default="ACTIVE") # ACTIVE, COMPLETED, ABANDONED
    created_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
    updated_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
