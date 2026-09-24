from typing import List, Dict, Any, Optional
import uuid
import logging
from aether.storage.repositories_goals import GoalRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("aether.cognitive.goals")

class GoalDecomposer:
    """
    Decomposes high-level agent goals into sequences of actionable tasks.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GoalRepository(session)

    async def decompose(self, agent_id: str, goal_id: str) -> List[Dict[str, Any]]:
        """
        Decomposes a goal into sub-tasks.
        Supports multi-agent assignment for collaborative goals.
        """
        goal = await self.repo.get_active_goals(agent_id)
        target_goal = next((g for g in goal if g.goal_id == goal_id), None)

        if not target_goal:
            logger.error(f"Goal {goal_id} not found or not active")
            return []

        # Lowercased copy is used for keyword matching; the original casing is
        # preserved in task params so downstream consumers see the goal verbatim.
        original_description = target_goal.description
        description = original_description.lower()

        # Check if goal is collaborative (explicit swarm/coalition tasks).
        # Plain "research" goals are handled by the SEARCH/READ/SUMMARIZE pipeline below.
        is_collaborative = "collaborate" in description or "collective" in description

        if is_collaborative:
            # Collaborative decomposition: assign some tasks to 'COALITION'
            tasks = [
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "COORDINATE", "params": {"goal": original_description}, "assignee": "LEADER"},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "COLLECT_DATA", "params": {"topic": original_description}, "assignee": "COALITION"},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "SYNTHESIZE", "params": {"target": "shared_graph"}, "assignee": "LEADER"},
            ]
        elif "synthesis" in description or "complex" in description or "research" in description:
            tasks = [
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "SEARCH", "params": {"query": original_description}},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "READ", "params": {"source": "top_results"}},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "SUMMARIZE", "params": {"target": "internal_memory"}},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "SYNTHESIZE", "params": {"target": "core_architecture"}},
            ]
        elif "summarize" in description:
            tasks = [
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "RETRIEVE", "params": {"topic": original_description}},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "GENERATE_SUMMARY", "params": {}},
            ]
        else:
            tasks = [
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "PLAN", "params": {"goal": original_description}},
                {"task_id": f"t_{uuid.uuid4().hex[:4]}", "action": "EXECUTE", "params": {}},
            ]

        logger.info(f"Decomposed goal {goal_id} into {len(tasks)} tasks. Collaborative: {is_collaborative}")
        return tasks

class GoalManager:
    """
    Orchestrates the goal lifecycle and autonomous task generation.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.decomposer = GoalDecomposer(session)
        self.repo = GoalRepository(session)

    async def get_next_autonomous_action(self, agent_id: str, drives: Optional[Dict[str, float]] = None) -> Optional[Dict[str, Any]]:
        """
        Determines the next autonomous action based on active goals.
        If drives are provided, they dynamically weight the priority of goals.
        Incorporates Core Values for priority boosting.
        """
        active_goals = await self.repo.get_active_goals(agent_id)
        if not active_goals:
            return None

        # Fetch Identity for Core Values
        from aether.storage.repositories import IdentityRepository
        id_repo = IdentityRepository(self.session)
        identity = await id_repo.get_by_id(agent_id)
        core_values = identity.get("core_values", []) if identity else []

        # Calculate weighted priorities.
        # - With drives: goal priorities are modulated by the drive alignment weight.
        # - Without drives: static priority is used (lowest = highest priority).
        # - Always: goals aligning with the agent's core values receive a boost.
        from aether.cognitive.drives import DriveManager
        drive_mgr = DriveManager(self.session) if drives else None

        # Sort goals by (base_priority * drive_weight * value_boost).
        # Lower result = higher priority.
        def get_weighted_priority(goal):
            weight = 1.0
            if drive_mgr is not None:
                weight = drive_mgr.calculate_priority_weight(goal.description, drives)

            # Value Alignment Boost
            # If goal description contains any core value, boost priority (decrease value)
            value_boost = 1.0
            for val in core_values:
                if val.lower() in goal.description.lower():
                    value_boost *= 0.8 # 20% priority boost

            return goal.priority * weight * value_boost

        sorted_goals = sorted(active_goals, key=get_weighted_priority)
        top_goal = sorted_goals[0]

        # Decompose into tasks
        tasks = await self.decomposer.decompose(agent_id, top_goal.goal_id)

        if tasks:
            # Return the first task to be executed
            return {
                "goal_id": top_goal.goal_id,
                "task": tasks[0],
                "priority": top_goal.priority
            }

        return None
