from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float
from aether.storage.models import Base
from datetime import datetime

class AgentDriveModel(Base):
    """
    Persistent storage for an agent's internal cognitive drives.
    Drives act as motivation weights that influence goal prioritization.
    """
    __tablename__ = "agent_drives"

    agent_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Cognitive Drives (Scale 0.0 to 1.0)
    # Curiosity: Drive to explore new information and resolve unknowns
    curiosity: Mapped[float] = mapped_column(Float, default=0.5)
    # Coherence: Drive to resolve logical contradictions and maintain consistency
    coherence: Mapped[float] = mapped_column(Float, default=0.5)
    # Stability: Drive to complete existing commitments and maintain current state
    stability: Mapped[float] = mapped_column(Float, default=0.5)

    updated_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
