import pytest
import asyncio
import time
from aether.storage.database import AsyncSessionLocal, engine
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_goals import GoalRepository
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.memory.manager import MemoryManager
from aether.memory.beliefs import BeliefManager
from aether.cognitive.reflection import ReflectionCycle
from aether.storage.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
async def test_reflection_and_belief_update():
    """Verify the reflection cycle correctly updates agent beliefs based on contradictory experience."""
    await init_db()
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        agent_id = "test_reflect_01"
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "Reflector", "Researcher", {}, [])

        belief_mgr = BeliefManager(session)
        # Initialize baseline belief
        await belief_mgr.update_or_create_belief(agent_id, "The world is static", 0.2)

        # Provide contradictory observation
        experience = {"event": "The world is changing rapidly", "context": "observation", "result": "surprise"}

        # Initialize reflection components
        from unittest.mock import MagicMock
        mock_vs = MagicMock()
        mem_mgr = MemoryManager(session, mock_vs)
        reflection = ReflectionCycle(session, mem_mgr, belief_mgr)

        # Execute reflection process
        result = await reflection.reflect(agent_id, experience)

        # Verify belief state update
        strong_beliefs = await belief_mgr.get_strongest_beliefs(agent_id, min_confidence=0.0)
        assert any("changing rapidly" in b["content"] for b in strong_beliefs)

@pytest.mark.asyncio
async def test_autonomous_goal_wake():
    """Verify that agents are automatically activated when associated with high-priority goals."""
    await init_db()
    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)

    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        goal_repo = GoalRepository(session)

        agent_id = "test_auto_01"
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "AutoAgent", "Worker", {}, [])

        # Define a high-level objective
        await goal_repo.create_goal("goal_auto_1", agent_id, "Research Aether Core", priority=1)

        # Trigger activation cycle
        await orch_manager.process_wake_events()

        # Verify automatic activation
        assert runtime.is_agent_awake(agent_id)

        # Verify task assignment to active state
        active_state = runtime.active_agents.get(agent_id)
        assert active_state is not None
        assert "current_task" in active_state
        task = active_state["current_task"]
        assert any(action in task.payload["action"] for action in ["SEARCH", "PLAN"])
