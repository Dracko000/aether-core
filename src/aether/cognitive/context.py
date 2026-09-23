from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class CognitivePath(BaseModel):
    path_type: str # "FAST" or "SLOW"
    reasoning_steps: List[str] = []

class ReasoningTrace(BaseModel):
    step: int
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None

class Plan(BaseModel):
    goal: str
    steps: List[Dict[str, Any]]
    status: str = "PENDING" # PENDING, IN_PROGRESS, COMPLETED
