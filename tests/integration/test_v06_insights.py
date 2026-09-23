import pytest
import asyncio
import uuid
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_experience import ExperienceGraphRepository
from aether.memory.manager import MemoryManager
from aether.memory.beliefs import BeliefManager
from aether.cognitive.reflection import ReflectionCycle
from aether.memory.vector_store import LocalVectorStore

@pytest.mark.asyncio
async def test_cognitive_insight_linking():
    """Verify that a belief can link multiple experience nodes as a 'Cognitive Insight'."""
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_id = "insight_agent"
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id, "default-model")
        
        exp_repo = ExperienceGraphRepository(session)
        
        # Create multiple related experience nodes
        node1_id = "node_1"
        node2_id = "node_2"
        await exp_repo.add_node(node1_id, agent_id, "Observation A: The sky is red")
        await exp_repo.add_node(node2_id, agent_id, "Observation B: The air is sulfurous")
        
        # Create an edge between them
        await exp_repo.add_edge("edge_1", node1_id, node2_id, rel_type="CO_OCCURRENCE")
        
        # Setup reflection
        vector_store = LocalVectorStore()
        mem_mgr = MemoryManager(session, vector_store)
        bel_mgr = BeliefManager(session)
        reflection = ReflectionCycle(session, mem_mgr, bel_mgr)
        
        # Experience that triggers reflection
        experience = {"event": "Volcanic eruption detected", "node_id": node1_id}
        
        # Reflect should find node1 and node2 via associative retrieval
        result = await reflection.reflect(agent_id, experience)
        
        # Check if a belief was created
        outcome = result["outcome"]
        assert outcome["status"] == "SUCCESS"
        
        # Verify the belief links multiple nodes
        belief_id = outcome["updated_belief_id"]
        from aether.storage.repositories_beliefs import BeliefRepository
        bel_repo = BeliefRepository(session)
        sources = await bel_repo.get_belief_sources(belief_id)
        
        assert len(sources) >= 2
        assert node1_id in sources
        assert node2_id in sources
        assert outcome.get("is_insight") is True

