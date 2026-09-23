import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, and_
from aether.storage.models_experience import ExperienceNodeModel, ExperienceEdgeModel

class ExperienceGraphRepository:
    """
    Manages graph operations for the Experience Graph.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_node(self, node_id: str, agent_id: str, content: str, embedding: list = None, importance: float = 1.0):
        stmt = insert(ExperienceNodeModel).values(
            node_id=node_id,
            agent_id=agent_id,
            content=content,
            embedding=json.dumps(embedding) if embedding else None,
            importance=importance
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def add_edge(self, edge_id: str, source_id: str, target_id: str, weight: float = 1.0, rel_type: str = "ASSOCIATION", description: str = None):
        stmt = insert(ExperienceEdgeModel).values(
            edge_id=edge_id,
            source_node_id=source_id,
            target_node_id=target_id,
            weight=weight,
            rel_type=rel_type,
            description=description
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_neighbors(self, node_id: str):
        """Retrieves all experience nodes linked to the specified node."""
        stmt = select(ExperienceNodeModel).join(
            ExperienceEdgeModel,
            (ExperienceEdgeModel.target_node_id == ExperienceNodeModel.node_id) &
            (ExperienceEdgeModel.source_node_id == node_id)
        )
        result = await self.session.execute(stmt)
        nodes = result.scalars().all()

        # Avoid mutating the model object directly to prevent SQLAlchemy autoflush issues
        return nodes

    async def get_node(self, node_id: str):
        stmt = select(ExperienceNodeModel).where(ExperienceNodeModel.node_id == node_id)
        result = await self.session.execute(stmt)
        node = result.scalar_one_or_none()
        return node

    def deserialize_embedding(self, node: ExperienceNodeModel):
        """Deserializes the embedding vector of a node."""
        if node and node.embedding and isinstance(node.embedding, str):
            return json.loads(node.embedding)
        return node.embedding if node else None

    async def find_by_content(self, agent_id: str, query: str):
        """Performs a keyword-based search for experience nodes."""
        stmt = select(ExperienceNodeModel).where(
            ExperienceNodeModel.agent_id == agent_id,
            ExperienceNodeModel.content.contains(query)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
