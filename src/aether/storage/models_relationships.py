from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey, Text
from aether.storage.models import Base
from datetime import datetime

class RelationshipModel(Base):
    """
    Persistent storage for relationships between agents.
    """
    __tablename__ = "agent_relationships"

    relationship_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    target_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    
    # Relationship metrics
    trust_score: Mapped[float] = mapped_column(Float, default=0.5) # Trust level [0.0, 1.0]
    familiarity: Mapped[float] = mapped_column(Float, default=0.0) # Familiarity level [0.0, 1.0]
    relationship_type: Mapped[str] = mapped_column(String, default="NEUTRAL") # Category (e.g., ALLY, RIVAL, SUPERVISOR)
    
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    updated_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
