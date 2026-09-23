import pytest
import asyncio
import uuid
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_experience import ExperienceGraphRepository

@pytest.mark.asyncio
async def test_experience_graph_flow():
    agent_id = "exp_test_agent"
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        exp_repo = ExperienceGraphRepository(session)
        
        await agent_repo.create(agent_id)
        
        # 1. Node instantiation
        node_a = "node_a"
        node_b = "node_b"
        await exp_repo.add_node(node_a, agent_id, "Learned about Rust ownership", embedding=[0.1, 0.2], importance=2.0)
        await exp_repo.add_node(node_b, agent_id, "Implementing a borrow checker", embedding=[0.15, 0.25], importance=1.5)

        # 2. Edge instantiation (Association)
        edge_id = "edge_ab"
        await exp_repo.add_edge(edge_id, node_a, node_b, weight=0.8, rel_type="CAUSAL", description="Knowledge of ownership led to implementation")

        # 3. Verify node retrieval
        node = await exp_repo.get_node(node_a)
        assert node is not None
        assert node.content == "Learned about Rust ownership"

        embedding = exp_repo.deserialize_embedding(node)
        assert embedding == [0.1, 0.2]

        # 4. Verify adjacency (A -> B)
        neighbors = await exp_repo.get_neighbors(node_a)
        assert len(neighbors) == 1
        assert neighbors[0].node_id == node_b

        # 5. Content-based search
        search_results = await exp_repo.find_by_content(agent_id, "borrow checker")
        assert len(search_results) == 1
        assert search_results[0].node_id == node_b

