from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey
from aether.storage.models import Base
from datetime import datetime, timezone

class AgentMigrationModel(Base):
    """
    Records the history of model migrations for an agent.
    """
    __tablename__ = "agent_migrations"

    migration_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)

    from_model_id: Mapped[str] = mapped_column(String)
    to_model_id: Mapped[str] = mapped_column(String)

    timestamp: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
    status: Mapped[str] = mapped_column(String, default="SUCCESS") # SUCCESS, FAILED
    notes: Mapped[str] = mapped_column(String, nullable=True)
