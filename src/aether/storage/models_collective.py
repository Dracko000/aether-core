from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, ForeignKey, JSON
from aether.storage.models import Base
from datetime import datetime, timezone

class CoalitionModel(Base):
    """
    Represents a temporary coalition of agents collaborating on a shared objective.
    """
    __tablename__ = "coalitions"

    coalition_id: Mapped[str] = mapped_column(String, primary_key=True)
    goal_id: Mapped[str] = mapped_column(String, index=True) # Associated high-level goal
    created_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
    status: Mapped[str] = mapped_column(String, default="ACTIVE") # Coalition status (ACTIVE, COMPLETED, DISBANDED)

class CoalitionMember(Base):
    """
    Association table for agents in a coalition.
    """
    __tablename__ = "coalition_members"

    coalition_id: Mapped[str] = mapped_column(String, ForeignKey("coalitions.coalition_id"), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), primary_key=True)
    joined_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
    role: Mapped[str] = mapped_column(String, default="MEMBER") # Role within coalition (e.g., LEADER, CONTRIBUTOR)

class SharedKnowledgeModel(Base):
    """
    Tracks knowledge fragments shared within the collective.
    """
    __tablename__ = "shared_knowledge"

    fragment_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)

    # Knowledge fragment content (JSON containing belief_id or experience_node_id and value)
    payload: Mapped[dict] = mapped_column(JSON)

    # Sharing context (e.g., coalition_id or 'PUBLIC')
    context_id: Mapped[str] = mapped_column(String, index=True)

    importance: Mapped[float] = mapped_column(Float, default=1.0)
    timestamp: Mapped[float] = mapped_column(Float, default=lambda: datetime.now(timezone.utc).timestamp())
