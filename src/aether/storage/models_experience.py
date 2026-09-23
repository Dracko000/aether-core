from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, ForeignKey
from aether.storage.models import Base
from datetime import datetime

class ExperienceNodeModel(Base):
    """
    A node in the Experience Graph representing a core conceptual unit of an experience.
    """
    __tablename__ = "experience_nodes"

    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    
    # The content of the experience (can be a summary or a pointer to episodic memory)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str] = mapped_column(Text, nullable=True) # Stored as JSON array of floats
    
    importance: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())

class ExperienceEdgeModel(Base):
    """
    An edge in the Experience Graph representing a relationship between two experiences.
    """
    __tablename__ = "experience_edges"

    edge_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_node_id: Mapped[str] = mapped_column(String, ForeignKey("experience_nodes.node_id"), index=True)
    target_node_id: Mapped[str] = mapped_column(String, ForeignKey("experience_nodes.node_id"), index=True)
    
    # Edge metadata
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    rel_type: Mapped[str] = mapped_column(String, default="ASSOCIATION") # e.g., CAUSAL, TEMPORAL, SIMILARITY
    description: Mapped[str] = mapped_column(String, nullable=True)
