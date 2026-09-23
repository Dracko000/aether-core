from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from aether.storage.models_beliefs import BeliefModel, belief_experience_link
from typing import List, Dict, Any, Optional

class BeliefRepository:
    """
    Manages the persistence of agent beliefs and their links to experience nodes.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_belief(self, belief_id: str, agent_id: str, content: str, confidence: float, source_ids: List[str] = None):
        # Create the core belief
        stmt = insert(BeliefModel).values(
            belief_id=belief_id,
            agent_id=agent_id,
            content=content,
            confidence=confidence,
            source_experience_id=source_ids[0] if source_ids else None
        )
        await self.session.execute(stmt)
        
        # Link to all source experience nodes
        if source_ids:
            links = [
                {"belief_id": belief_id, "experience_node_id": node_id}
                for node_id in source_ids
            ]
            await self.session.execute(insert(belief_experience_link), links)
            
        await self.session.commit()

    async def get_beliefs(self, agent_id: str, min_confidence: float = 0.0):
        stmt = select(BeliefModel).where(
            BeliefModel.agent_id == agent_id,
            BeliefModel.confidence >= min_confidence
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_belief(self, belief_id: str, confidence: float):
        stmt = update(BeliefModel).where(
            BeliefModel.belief_id == belief_id
        ).values(confidence=confidence)
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_belief_sources(self, belief_id: str) -> List[str]:
        """Retrieves all experience node IDs linked to a specific belief."""
        stmt = select(belief_experience_link.c.experience_node_id).where(
            belief_experience_link.c.belief_id == belief_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
