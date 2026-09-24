from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from aether.api.dependencies import get_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from pydantic import BaseModel

class AgentCreate(BaseModel):
    agent_id: str
    name: str
    role: str
    personality: dict
    skills: list
    core_values: list = []

router = APIRouter()

@router.post("/")
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent_repo = AgentRepository(db)
    identity_repo = IdentityRepository(db)

    try:
        await agent_repo.create(agent_data.agent_id)
        await identity_repo.create(
            agent_data.agent_id,
            agent_data.name,
            agent_data.role,
            agent_data.personality,
            agent_data.skills,
            core_values=agent_data.core_values
        )
        return {"status": "success", "agent_id": agent_data.agent_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
