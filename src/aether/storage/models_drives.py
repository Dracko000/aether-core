from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float
from aether.storage.models import Base
from datetime import datetime, timezone

class AgentDriveModel(Base):
    """
    Persistent storage for an agent's internal cognitive drives and emotional states.
    Drives act as motivation weights, while emotions modulate those weights.
    """
    __tablename__ = "agent_drives"

    agent_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Cognitive Drives (Scale 0.0 to 1.0)
    curiosity: Mapped[float] = mapped_column(Float, default=0.5)
    coherence: Mapped[float] = mapped_column(Float, default=0.5)
    stability: Mapped[float] = mapped_column(Float, default=0.5)

    # Emotional States (Scale 0.0 to 1.0)
    frustration: Mapped[float] = mapped_column(Float, default=0.0)
    satisfaction: Mapped[float] = mapped_column(Float, default=0.0)
    anxiety: Mapped[float] = mapped_column(Float, default=0.0)
    joy: Mapped[float] = mapped_column(Float, default=0.0)

    updated_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
