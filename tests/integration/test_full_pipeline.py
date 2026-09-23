import pytest
import asyncio
import os
from aether.storage.database import AsyncSessionLocal, init_db
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.model.mock import MockAdapter
from aether.model.manager import ModelManager
from aether.memory.vector_store import LocalVectorStore
from aether.memory.manager import MemoryManager
from aether.tools.registry import registry
from aether.tools.builtin.filesystem import register_filesystem_tools

@pytest.mark.asyncio
async def test_aether_core_full_pipeline():
    """
    End-to-End System Validation:
    Traces a request through the full cognitive pipeline: Orchestration -> Runtime -> Cognitive Engine -> Memory -> Tools -> Consolidation.
    """
    # 1. Infrastructure Provisioning
    async with AsyncSessionLocal() as session:
        await init_db()

        # Component Initialization
        adapter = MockAdapter()
        model_manager = ModelManager(adapter)
        vector_store = LocalVectorStore()
        memory_manager = MemoryManager(session=session, vector_store=vector_store)
        runtime = AgentRuntime()
        orchestrator = OrchestrationManager(runtime)

        # Tool Registration
        register_filesystem_tools()

        await orchestrator.start()

        # 2. Agent Identity Provisioning
        agent_id = "smoke_agent_001"
        from aether.storage.repositories import AgentRepository, IdentityRepository
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)

        # Ensure clean state for the agent
        existing_agent = await agent_repo.get(agent_id)
        if not existing_agent:
            await agent_repo.create(agent_id)

        # Ensure identity record exists
        existing_id = await id_repo.get_by_id(agent_id)
        if not existing_id:
            await id_repo.create(
                agent_id=agent_id,
                name="Smoke Tester",
                role="Quality Assurance",
                personality={"diligent": True},
                skills=["filesystem"]
            )

        # Authorization
        from aether.tools.permissions import PermissionManager
        pm = PermissionManager(session)
        await pm.grant_permission(agent_id, "filesystem.read")

        # 3. Pipeline Execution
        # Provision test artifact for tool retrieval
        test_file = "smoke_test.txt"
        with open(test_file, "w") as f:
            f.write("System verified: Aether Core is operational.")

        # Dispatch task requiring tool invocation
        task_payload = {"query": f"Read the content of {test_file}", "type": "tool_use"}
        task_id = await orchestrator.assign_task(agent_id, task_payload)

        # Verify state transition: Sleeping -> Awakened -> Thinking
        assert runtime.is_agent_awake(agent_id)
        assert runtime.active_agents[agent_id]["state"].name == "THINKING"

        # Execute cognitive processing path
        from aether.cognitive.engine import CognitiveEngine
        engine = CognitiveEngine(model_manager, memory_manager)

        # Process query through cognitive engine
        response = await engine.execute(agent_id=agent_id, query=task_payload["query"])

        # Verify response generation
        assert response is not None

        # Execute tool invocation via ToolExecutor
        from aether.tools.executor import ToolExecutor
        executor = ToolExecutor(session)
        tool_result = await executor.execute(agent_id, "filesystem.read", {"path": test_file})
        assert "System verified" in tool_result

        # 4. Memory Consolidation
        # Integrate experience into long-term memory
        experience = {
            "event": "Verified system operational",
            "context": "Smoke test execution",
            "result": tool_result
        }
        await memory_manager.consolidate(agent_id, experience)

        # Verify retrieval of consolidated fact
        memories = await memory_manager.retrieve(agent_id, "system operational")
        assert len(memories) > 0

        # Cleanup
        os.remove(test_file)
        await orchestrator.stop()
