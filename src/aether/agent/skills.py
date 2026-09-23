from pydantic import BaseModel

class Skill(BaseModel):
    skill_id: str
    name: str
    description: str
    proficiency: float # 0.0 to 1.0
