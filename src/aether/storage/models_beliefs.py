from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, ForeignKey, Table, Column
from aether.storage.models import Base
from datetime import datetime

# Association table for multi-node belief linking (Cognitive Insights)
belief_experience_link = Table(
    "belief_experience_links",
    Base.metadata,
    Column("belief_id", String, ForeignKey("agent_beliefs.belief_id"), primary_key=True),
    Column("experience_node_id", String, ForeignKey("experience_nodes.node_id"), primary_key=True),
)

class BeliefModel(Base):
    """
    Represents a subjective proposition or belief held by an agent.
    """
    __tablename__ = "agent_beliefs"

    belief_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)

    content: Mapped[str] = mapped_column(Text) # Core propositional claim
    confidence: Mapped[float] = mapped_column(Float, default=0.5) # Confidence interval [0.0, 1.0]

    # Reference to the primary experience that formed or updated this belief
    # Now optional as multi-links are stored in belief_experience_link
    source_experience_id: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
    updated_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
    last_verified: Mapped[float] = mapped_column(Float, nullable=True) # For meta-cognitive decay and auditing
