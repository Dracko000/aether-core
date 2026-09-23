import pytest
import asyncio
import uuid
import time
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_events import AgentEventRepository
from aether.storage.repositories_goals import GoalRepository
from aether.storage.repositories_experience import ExperienceGraphRepository
from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.agent.lifecycle import AgentState

@pytest.mark.asyncio
async def test_v02_full_life_cycle():
    # Setup
    agent_a_id = "agent_a"
    agent_b_id = "agent_b"
    
    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        
        # Create Agent A
        await agent_repo.create(agent_a_id)
        await id_repo.create(agent_a_id, "Agent A", "Sender", {}, [])
        
        # Create Agent B
        await agent_repo.create(agent_b_id)
        await id_repo.create(agent_b_id, "Agent B", "Receiver", {}, [])

    runtime = AgentRuntime()
    orch_manager = OrchestrationManager(runtime)
    
    # --- STEP 1: Social Wake-up ---
    # Agent A sends message to Agent B
    await orch_manager.send_agent_message(agent_a_id, agent_b_id, "Hello B, wake up and work!")
    
    # Process the wake event (simulating scheduler tick)
    await orch_manager.process_wake_events()
    
    assert runtime.is_agent_awake(agent_b_id), "Agent B should be awake after receiving message"
    assert runtime.active_agents[agent_b_id]["state"] == AgentState.AWAKENED

    # --- STEP 2: Task Assignment ---
    task_payload = {"task": "Analyze the current system state"}
    await orch_manager.assign_task(agent_b_id, task_payload)
    
    # Verify transition to THINKING
    assert runtime.active_agents[agent_b_id]["state"] == AgentState.THINKING
    assert "current_task" in runtime.active_agents[agent_b_id]

    # --- STEP 3: Experience Recording ---
    async with AsyncSessionLocal() as session:
        exp_repo = ExperienceGraphRepository(session)
        node_id = "exp_1"
        await exp_repo.add_node(node_id, agent_b_id, "Successfully processed first system task", importance=2.0)
        
        # Verify node exists
        node = await exp_repo.get_node(node_id)
        assert node is not None
        assert "Successfully" in node.content

    # --- STEP 4: Goal Setting ---
    async with AsyncSessionLocal() as session:
        goal_repo = GoalRepository(session)
        goal_id = "goal_1"
        await goal_repo.create_goal(goal_id, agent_b_id, "Become the lead architect of Aether", priority=1)
        
        # Verify goal is active
        active_goals = await goal_repo.get_active_goals(agent_b_id)
        assert len(active_goals) == 1
        assert active_goals[0].description == "Become the lead architect of Aether"

    # --- STEP 5: Sleep Cycle ---
    await runtime.sleep(agent_b_id)
    
    assert not runtime.is_agent_awake(agent_b_id), "Agent B should be removed from runtime after sleep"
    
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get(agent_b_id)
        assert agent.status == AgentState.SLEEPING.name

