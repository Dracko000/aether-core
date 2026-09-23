from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, ForeignKey, Boolean, JSON
from aether.storage.models import Base
from datetime import datetime

class AgentMessageModel(Base):
    """
    Persistent storage for asynchronous communication between agents.
    """
    __tablename__ = "agent_messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    sender_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)
    receiver_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), index=True)

    content: Mapped[str] = mapped_column(Text)
    # Structured knowledge payloads (e.g., {"fragment_id": "...", "type": "belief"})
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)

    timestamp: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
