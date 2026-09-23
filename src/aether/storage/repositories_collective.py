from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, update
from aether.storage.models_collective import CoalitionModel, CoalitionMember, SharedKnowledgeModel
from typing import List, Optional, Dict, Any

class CollectiveRepository:
    """
    Manages the persistence of shared knowledge and agent coalitions.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Coalition Management ---
    async def create_coalition(self, coalition_id: str, goal_id: str):
        stmt = insert(CoalitionModel).values(
            coalition_id=coalition_id,
            goal_id=goal_id
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def add_member_to_coalition(self, coalition_id: str, agent_id: str, role: str = "MEMBER"):
        stmt = insert(CoalitionMember).values(
            coalition_id=coalition_id,
            agent_id=agent_id,
            role=role
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_coalition_members(self, coalition_id: str) -> List[str]:
        stmt = select(CoalitionMember.agent_id).where(CoalitionMember.coalition_id == coalition_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_coalition_by_goal(self, goal_id: str) -> Optional[CoalitionModel]:
        stmt = select(CoalitionModel).where(CoalitionModel.goal_id == goal_id, CoalitionModel.status == "ACTIVE")
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Shared Knowledge ---
    async def share_fragment(self, fragment_id: str, source_id: str, payload: dict, context_id: str, importance: float = 1.0):
        stmt = insert(SharedKnowledgeModel).values(
            fragment_id=fragment_id,
            source_agent_id=source_id,
            payload=payload,
            context_id=context_id,
            importance=importance
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_fragments_by_context(self, context_id: str) -> List[SharedKnowledgeModel]:
        stmt = select(SharedKnowledgeModel).where(SharedKnowledgeModel.context_id == context_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def remove_fragment(self, fragment_id: str):
        stmt = delete(SharedKnowledgeModel).where(SharedKnowledgeModel.fragment_id == fragment_id)
        await self.session.execute(stmt)
        await self.session.commit()
