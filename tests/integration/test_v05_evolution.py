import pytest
import asyncio
from aether.storage.database import AsyncSessionLocal, engine
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.model.capabilities import CapabilityMatrix, ModelCapabilities
from aether.model.migration import ModelMigrationManager
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.storage.models import Base
from aether.storage.repositories_goals import GoalRepository

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
async def test_autonomous_evolution_pipeline():
    """Verify the autonomous evolution pipeline: capability gap detection leading to model migration."""
    await init_db()

    # 1. Capability Matrix Configuration
    matrix = CapabilityMatrix()
    matrix.register_model(ModelCapabilities(model_id="basic-model", max_context=4096, reasoning_level=1))
    matrix.register_model(ModelCapabilities(model_id="expert-model", max_context=128000, reasoning_level=3))

    # 2. Runtime and Orchestration Setup
    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime, capability_matrix=matrix)

    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        goal_repo = GoalRepository(session)
        id_repo = IdentityRepository(session)

        agent_id = "evo_agent_01"
        # Provision agent with basic model capabilities
        await agent_repo.create(agent_id, model_id="basic-model")
        # Provision corresponding identity record
        await id_repo.create(
            agent_id=agent_id,
            name="Evolutionary Agent",
            role="Researcher",
            personality={"trait": "curious"},
            skills=["analysis"]
        )

        # 3. Objective Specification
        # Assign a complex goal requiring high reasoning capabilities (reasoning_level 3)
        goal_id = "goal_complex_01"
        await goal_repo.create_goal(goal_id, agent_id, "Perform a complex synthesis of aether core architecture", priority=1)

        # 4. Activation and Evolution
        # Trigger activation cycle to detect capability gap and initiate migration
        await orch_manager.process_wake_events()

        # 5. Migration Verification
        updated_agent = await agent_repo.get(agent_id)
        assert updated_agent.model_id == "expert-model", f"Agent should have evolved to expert-model, but is {updated_agent.model_id}"

        # 6. Continuity Verification
        assert runtime.is_agent_awake(agent_id)

        # 7. Migration Audit
        from aether.storage.repositories_evolution import EvolutionRepository
        evo_repo = EvolutionRepository(session)
        history = await evo_repo.get_migration_history(agent_id)
        assert len(history) > 0
        assert history[0].from_model_id == "basic-model"
        assert history[0].to_model_id == "expert-model"
