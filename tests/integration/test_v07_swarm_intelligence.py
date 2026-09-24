import pytest
import asyncio
import uuid
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_collective import CollectiveRepository
from aether.storage.repositories_beliefs import BeliefRepository
from aether.memory.manager import MemoryManager
from aether.memory.beliefs import BeliefManager
from aether.cognitive.swarm import SwarmReflectionManager
from aether.memory.vector_store import LocalVectorStore

@pytest.mark.asyncio
async def test_shared_retrieval():
    """Verify an agent can retrieve a memory fragment shared by another member of its coalition."""
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_id = "agent_01"
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id, "default-model")
        
        # Share a fragment in 'PUBLIC' context
        col_repo = CollectiveRepository(session)
        await col_repo.share_fragment(
            fragment_id="frag_1",
            source_id="agent_02",
            payload={"content": "The quantum core is unstable"},
            context_id="PUBLIC",
            importance=0.8
        )
        
        # Setup memory manager
        vector_store = LocalVectorStore()
        mem_mgr = MemoryManager(session, vector_store)
        
        # Retrieve should now include the collective fragment
        results = await mem_mgr.retrieve(agent_id, "quantum core")
        
        assert any(res["type"] == "collective" and "unstable" in res["content"] for res in results)

@pytest.mark.asyncio
async def test_swarm_convergence():
    """Verify that a coalition of agents can synthesize a collective insight."""
    async with AsyncSessionLocal() as session:
        await init_db()
        
        agent_repo = AgentRepository(session)
        agents = ["agent_1", "agent_2", "agent_3"]
        for a in agents:
            await agent_repo.create(a, "default-model")
            
        col_repo = CollectiveRepository(session)
        coalition_id = "coal_1"
        await col_repo.create_coalition(coalition_id, "goal_1")
        for a in agents:
            await col_repo.add_member_to_coalition(coalition_id, a)
            
        # Setup swarm manager
        vector_store = LocalVectorStore()
        mem_mgr = MemoryManager(session, vector_store)
        swarm_mgr = SwarmReflectionManager(session, mem_mgr)
        
        experience = {"event": "Detection of an anomalous signal"}
        result = await swarm_mgr.coordinate_swarm_reflection(coalition_id, "goal_1", experience)
        
        assert result["status"] == "SUCCESS"
        assert "Collective Insight" in result["content"]
        
        # Verify propagation to members' belief stores
        bel_repo = BeliefRepository(session)
        
        for a in agents:
            beliefs = await bel_repo.get_beliefs(a)
            assert any("Collective Insight" in b.content for b in beliefs)
