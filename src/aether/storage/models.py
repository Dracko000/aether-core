from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, JSON, DateTime, Float, ForeignKey
from typing import List
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Agent(Base):
    __tablename__ = "agents"
    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="CREATED") # Lifecycle state
    model_id: Mapped[str] = mapped_column(String, default="default-model")

class Identity(Base):
    __tablename__ = "identities"
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    personality: Mapped[dict] = mapped_column(JSON)
    skills: Mapped[list] = mapped_column(JSON)
    core_values: Mapped[list] = mapped_column(JSON, default=lambda: []) # High-level ethical/priority principles

class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"))
    timestamp: Mapped[float] = mapped_column(Float, default=lambda: datetime.utcnow().timestamp())
    event: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text)
    lesson: Mapped[str] = mapped_column(Text, nullable=True)

class SemanticMemory(Base):
    __tablename__ = "semantic_memories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"))
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[float] = mapped_column(Float)

class ProceduralMemory(Base):
    __tablename__ = "procedural_memories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"))
    procedure: Mapped[str] = mapped_column(Text)
    steps: Mapped[list] = mapped_column(JSON)
    success_rate: Mapped[float] = mapped_column(Float)

class LongTermMemory(Base):
    __tablename__ = "longterm_memories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.agent_id"))
    fact: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[float] = mapped_column(Float)
