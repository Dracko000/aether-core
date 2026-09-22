from pydantic import BaseModel, Field
from typing import List, Dict, Any

class AgentIdentity(BaseModel):
    """
    Domain model for an agent's persistent identity.
    """
    agent_id: str
    name: str
    role: str
    personality: Dict[str, Any] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
