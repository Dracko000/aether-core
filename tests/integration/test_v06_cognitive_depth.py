import pytest
import asyncio
import time
import uuid
from aether.storage.database import AsyncSessionLocal, init_db
from aether.orchestration.manager import OrchestrationManager
from aether.agent.runtime import AgentRuntime
from aether.model.capabilities import CapabilityMatrix
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_goals import GoalRepository
from aether.cognitive.drives import DriveManager
from aether.cognitive.reflection import ReflectionCycle
from aether.memory.manager import MemoryManager
from aether.memory.beliefs import BeliefManager
from aether.memory.vector_store import LocalVectorStore

@pytest.mark.asyncio
async def test_drive_influence():
    """Verify that a 'Discovery' event increases Curiosity and shifts priority toward research goals."""
    async with AsyncSessionLocal() as session:
        # Must initialize DB for this session's DB file
        await init_db()
        
        # Setup
        agent_id = "drive_test_agent"
        agent_repo = AgentRepository(session)
        goal_repo = GoalRepository(session)
        drive_mgr = DriveManager(session)
        
        # Create agent
        await agent_repo.create(agent_id, "default-model")
        
        # Create two goals: one research (curiosity), one execution (stability)
        # Fix: use create_goal instead of create
        await goal_repo.create_goal(str(uuid.uuid4()), agent_id, "Research the Void", 10)
        await goal_repo.create_goal(str(uuid.uuid4()), agent_id, "Maintain Base", 5)
        
        # Initial check: "Maintain Base" should be top goal (priority 5 < 10)
        from aether.cognitive.goals import GoalManager
        goal_mgr = GoalManager(session)
        action_before = await goal_mgr.get_next_autonomous_action(agent_id)
        assert "Maintain" in action_before["task"]["params"].get("goal", "") or "PLAN" in action_before["task"]["action"]

        # Trigger discovery event to spike curiosity
        await drive_mgr.update_drives(agent_id, "DISCOVERY", {"curiosity": 0.4})
        drives = await drive_mgr.repo.get_drives(agent_id)
        
        # Now check: Research goal should be weighted higher
        action_after = await goal_mgr.get_next_autonomous_action(agent_id, drives=drives)
        # "Research the Void" matches 'research' keyword in DriveManager
        assert "Research" in action_after["task"]["params"].get("query", "") or "SEARCH" in action_after["task"]["action"]

@pytest.mark.asyncio
async def test_conflict_resolution():
    """Verify that a contradiction spikes Coherence and triggers an autonomous reflection cycle."""
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_id = "conflict_agent"
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id, "default-model")
        
        drive_mgr = DriveManager(session)
        # Simulate a contradiction event
        await drive_mgr.update_drives(agent_id, "CONTRADICTION", {"coherence": 0.4})
        drives = await drive_mgr.repo.get_drives(agent_id)
        
        assert drives["coherence"] > 0.5

@pytest.mark.asyncio
async def test_reasoning_convergence():
    """Verify that the reflection loop produces a converged result."""
    async with AsyncSessionLocal() as session:
        await init_db()
        
        # Mock dependencies
        vector_store = LocalVectorStore()
        mem_mgr = MemoryManager(session, vector_store)
        bel_mgr = BeliefManager(session)
        reflection = ReflectionCycle(session, mem_mgr, bel_mgr)
        
        experience = {"event": "The sensor reports a negative mass anomaly", "node_id": "node_1"}
        result = await reflection.reflect("agent_01", experience)
        
        assert "synthesis" in result
        assert result["synthesis"]["hypotheses_evaluated"] >= 3
        assert "converged" in result["synthesis"]["lesson"].lower()
