import pytest
import asyncio
import uuid
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_goals import GoalRepository

@pytest.mark.asyncio
async def test_goal_lifecycle():
    agent_id = "goal_test_agent"
    goal_id = str(uuid.uuid4())
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        goal_repo = GoalRepository(session)
        
        await agent_repo.create(agent_id)
        
        # 1. Create goal
        await goal_repo.create_goal(
            goal_id=goal_id,
            agent_id=agent_id,
            description="Learn to code in Rust",
            priority=1
        )
        
        # 2. Retrieve active goals
        goals = await goal_repo.get_active_goals(agent_id)
        assert len(goals) == 1
        assert goals[0].goal_id == goal_id
        assert goals[0].description == "Learn to code in Rust"
        
        # 3. Complete goal
        await goal_repo.complete_goal(goal_id)
        goals_after = await goal_repo.get_active_goals(agent_id)
        assert len(goals_after) == 0

