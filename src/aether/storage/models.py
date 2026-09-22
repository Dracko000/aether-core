from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, JSON
from typing import List

class Base(DeclarativeBase):
    pass

class Agent(Base):
    __tablename__ = "agents"
    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="CREATED") # Lifecycle state

class Identity(Base):
    __tablename__ = "identities"
    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    personality: Mapped[dict] = mapped_column(JSON)
    skills: Mapped[list] = mapped_column(JSON)
