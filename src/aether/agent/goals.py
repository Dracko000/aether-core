from pydantic import BaseModel
from typing import List, Optional

class Goal(BaseModel):
    """
    Represents a cognitive objective within the agent's goal hierarchy.
    """
    goal_id: str
    description: str
    priority: int
    status: str = "PENDING" # Possible values: PENDING, IN_PROGRESS, COMPLETED, FAILED
    subgoals: List[str] = []
