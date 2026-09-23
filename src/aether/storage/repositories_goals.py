from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, update
from aether.storage.models_goals import AgentGoalModel

class GoalRepository:
    """
    Manages the persistence of agent goals.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_goal(self, goal_id: str, agent_id: str, description: str, priority: int = 10):
        stmt = insert(AgentGoalModel).values(
            goal_id=goal_id,
            agent_id=agent_id,
            description=description,
            priority=priority
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_active_goals(self, agent_id: str):
        stmt = select(AgentGoalModel).where(
            AgentGoalModel.agent_id == agent_id,
            AgentGoalModel.status == "ACTIVE"
        ).order_by(AgentGoalModel.priority.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def complete_goal(self, goal_id: str):
        stmt = update(AgentGoalModel).where(
            AgentGoalModel.goal_id == goal_id
        ).values(status="COMPLETED", is_completed=True)
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_goal(self, goal_id: str):
        stmt = delete(AgentGoalModel).where(AgentGoalModel.goal_id == goal_id)
        await self.session.execute(stmt)
        await self.session.commit()
