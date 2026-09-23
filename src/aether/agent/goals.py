from pydantic import BaseModel
from typing import List, Optional

class Goal(BaseModel):
    goal_id: str
    description: str
    priority: int
    status: str = "PENDING" # PENDING, IN_PROGRESS, COMPLETED, FAILED
    subgoals: List[str] = []
