from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from aether.storage.models_relationships import RelationshipModel

class RelationshipRepository:
    """
    Manages the persistence of agent relationships and trust metrics.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def set_relationship(self, source_id: str, target_id: str, rel_type: str = "NEUTRAL", trust: float = 0.5, notes: str = None):
        # Upsert relationship record
        stmt = select(RelationshipModel).where(
            RelationshipModel.source_agent_id == source_id,
            RelationshipModel.target_agent_id == target_id
        )
        result = await self.session.execute(stmt)
        rel = result.scalar_one_or_none()

        if rel:
            rel.relationship_type = rel_type
            rel.trust_score = trust
            rel.notes = notes
        else:
            rel_id = f"rel_{source_id}_{target_id}"
            stmt = insert(RelationshipModel).values(
                relationship_id=rel_id,
                source_agent_id=source_id,
                target_agent_id=target_id,
                relationship_type=rel_type,
                trust_score=trust,
                notes=notes
            )
            await self.session.execute(stmt)
        
        await self.session.commit()

    async def get_relationship(self, source_id: str, target_id: str):
        stmt = select(RelationshipModel).where(
            RelationshipModel.source_agent_id == source_id,
            RelationshipModel.target_agent_id == target_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
