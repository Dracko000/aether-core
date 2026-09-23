from pydantic import BaseModel

class Skill(BaseModel):
    """
    Represents a discrete capability or expertise held by an agent.
    """
    skill_id: str
    name: str
    description: str
    proficiency: float # Range: 0.0 (novice) to 1.0 (expert)
