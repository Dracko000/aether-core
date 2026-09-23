import pytest
import asyncio
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository
from aether.model.capabilities import CapabilityMatrix, ModelCapabilities
from aether.model.migration import ModelMigrationManager
from aether.agent.runtime import AgentRuntime

@pytest.mark.asyncio
async def test_model_migration_flow():
    agent_id = "migration_test_agent"
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        await agent_repo.create(agent_id, model_id="llama-7b")
    
    # Setup Capability Matrix
    matrix = CapabilityMatrix()
    matrix.register_model(ModelCapabilities(
        model_id="llama-7b", 
        max_context=4096, 
        reasoning_level=1
    ))
    matrix.register_model(ModelCapabilities(
        model_id="llama-70b", 
        max_context=32768, 
        reasoning_level=3
    ))
    
    runtime = AgentRuntime()
    migration_mgr = ModelMigrationManager(runtime, matrix)
    
    # Migrate agent from 7b to 70b
    success = await migration_mgr.migrate_agent(agent_id, "llama-70b")
    assert success is True
    
    # Verify persistence
    async with AsyncSessionLocal() as session:
        agent = await agent_repo.get(agent_id)
        assert agent.model_id == "llama-70b"

