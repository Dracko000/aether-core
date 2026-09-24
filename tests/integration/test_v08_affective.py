import pytest
import asyncio
import uuid
import logging
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.cognitive.drives import DriveManager
from aether.cognitive.goals import GoalManager
from aether.cognitive.emotions import EmotionManager
from aether.storage.repositories_goals import GoalRepository
from aether.cognitive.reflection import ReflectionCycle
from aether.memory.manager import MemoryManager
from aether.memory.beliefs import BeliefManager
from aether.memory.vector_store import LocalVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_affective")

@pytest.mark.asyncio
async def test_emotional_modulation_of_drives():
    """
    Verify that emotional states (Joy, Frustration) correctly modulate 
    the priority weights of cognitive drives.
    """
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_id = "emotion_test_agent"
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id, "default-model")
        
        drive_mgr = DriveManager(session)
        emotion_mgr = EmotionManager(session)
        
        # Goal targeting curiosity (e.g., "research")
        goal_desc = "Research the quantum anomaly"
        
        # Baseline drives: curiosity = 0.5
        drives = {"curiosity": 0.5, "coherence": 0.5, "stability": 0.5}
        weight_baseline = drive_mgr.calculate_priority_weight(goal_desc, drives)
        
        # 1. Boost with Joy: Should increase curiosity modifier -> lower weight (higher priority)
        drives_joy = {"curiosity": 0.5, "coherence": 0.5, "stability": 0.5, "joy": 0.8}
        weight_joy = drive_mgr.calculate_priority_weight(goal_desc, drives_joy)
        
        # 2. Penalize with Frustration: Should decrease curiosity modifier -> higher weight (lower priority)
        drives_frust = {"curiosity": 0.5, "coherence": 0.5, "stability": 0.5, "frustration": 0.8}
        weight_frust = drive_mgr.calculate_priority_weight(goal_desc, drives_frust)
        
        logger.info(f"Weights - Baseline: {weight_baseline}, Joy: {weight_joy}, Frust: {weight_frust}")
        
        assert weight_joy < weight_baseline, "Joy should increase curiosity priority"
        assert weight_frust > weight_baseline, "Frustration should decrease curiosity priority"

@pytest.mark.asyncio
async def test_core_value_alignment_boost():
    """
    Verify that goals aligning with core values receive a priority boost.
    """
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_id = "value_test_agent"
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        
        await agent_repo.create(agent_id, "default-model")
        # Set core values to include "Truth"
        await id_repo.update_identity(agent_id, {
            "name": "Seeker",
            "role": "Researcher",
            "personality": {},
            "skills": [],
            "core_values": ["Truth", "Harmony"]
        })
        
        goal_repo = GoalRepository(session)
        # Goal A: Aligned with "Truth"
        goal_id_a = str(uuid.uuid4())
        await goal_repo.create_goal(goal_id_a, agent_id, "Discover the absolute Truth of the universe", 10)
        
        # Goal B: Not aligned
        goal_id_b = str(uuid.uuid4())
        await goal_repo.create_goal(goal_id_b, agent_id, "Organize the file system", 10)
        
        goal_mgr = GoalManager(session)
        
        # We test get_next_autonomous_action with specific goals
        # To isolate, we can temporarily remove the other goal or check which one is picked
        
        # Test Goal A (Aligned)
        # Since we can't easily isolate a single goal in get_next_autonomous_action without 
        # it seeing others, we check that Truth goal is preferred over others of same priority
        
        action = await goal_mgr.get_next_autonomous_action(agent_id)
        assert "Truth" in action["task"]["params"].get("query", "") or "Truth" in action["task"]["params"].get("goal", ""), \
            "Aligned goal should be prioritized over non-aligned goal of same base priority"

@pytest.mark.asyncio
async def test_reflection_emotional_feedback():
    """
    Verify that the ReflectionCycle updates emotional states based on the synthesis outcome.
    """
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_id = "reflect_emotion_agent"
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id, "default-model")
        
        # Setup reflection dependencies
        vector_store = LocalVectorStore()
        mem_mgr = MemoryManager(session, vector_store)
        bel_mgr = BeliefManager(session)
        reflection = ReflectionCycle(session, mem_mgr, bel_mgr)
        emotion_mgr = EmotionManager(session)
        
        # Baseline emotions
        await emotion_mgr.update_emotion(agent_id, "satisfaction", 0.0)
        await emotion_mgr.update_emotion(agent_id, "frustration", 0.0)
        
        # 1. Force a REINFORCE outcome (no contradictions)
        experience_simple = {"event": "The sun rises in the east", "node_id": "node_simple"}
        # We need to ensure no contradictions. Since we have no beliefs yet, it's REINFORCE.
        await reflection.reflect(agent_id, experience_simple)

        from aether.storage.repositories_drives import DriveRepository
        drive_repo = DriveRepository(session)
        state_reinforce = await drive_repo.get_drives(agent_id)

        assert state_reinforce.satisfaction > 0.0, "REINFORCE should increase satisfaction"
        
        # 2. Force a REVISE outcome (contradiction)
        # First, create a belief
        await bel_mgr.update_or_create_belief(agent_id, "The moon is made of cheese", 0.9)
        
        experience_conflict = {"event": "The moon is made of rock", "node_id": "node_conflict"}
        # Reflection should find contradiction -> REVISE
        await reflection.reflect(agent_id, experience_conflict)
        
        state_revise = await drive_repo.get_drives(agent_id)
        assert state_revise.frustration > state_reinforce.frustration, "REVISE should increase frustration"
