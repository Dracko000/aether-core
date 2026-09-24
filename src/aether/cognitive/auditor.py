from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from aether.storage.repositories_beliefs import BeliefRepository

logger = logging.getLogger("aether.cognitive.auditor")

class CognitiveAuditor:
    """
    The 'conscience' of the Aether agent.
    Monitors cognitive processes for reasoning quality, dissonance, and alignment.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BeliefRepository(session)

    async def audit_reflection(self, agent_id: str, synthesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates the quality of a reflection synthesis.
        Checks for:
        1. Convergence robustness (avoiding fallback hypotheses).
        2. Cognitive dissonance (contradiction with high-confidence beliefs).
        """
        logger.info(f"Auditing reflection synthesis for agent {agent_id}...")

        # 1. Check for fallback synthesis
        # If the final result is just a repeat of the event without synthesis, it's low quality
        is_robust = True
        if synthesis.get("hypotheses_evaluated", 0) < 2:
            is_robust = False
            logger.warning(f"Agent {agent_id} reflection used insufficient hypothesis set.")

        # 2. Detect Dissonance
        # Compare synthesis content against the agent's most stable beliefs
        dissonance_detected = False
        stable_beliefs = await self.repo.get_beliefs(agent_id, min_confidence=0.8)

        synthesis_content = synthesis.get("content", "").lower()
        for b in stable_beliefs:
            # Simulation: if the content is radically different but covers the same topic, flag it
            # In a real system, we'd use an LLM or a logic-checker for contradictions
            if any(word in synthesis_content for word in b.content.lower().split() if len(word) > 5):
                # If it matches a stable belief but the action is 'REVISE', it's a point of dissonance
                if synthesis.get("action") == "REVISE":
                    dissonance_detected = True
                    logger.info(f"Cognitive dissonance detected for agent {agent_id} regarding belief {b.belief_id}")
                    break

        return {
            "is_robust": is_robust,
            "dissonance_detected": dissonance_detected,
            "quality_score": 1.0 if (is_robust and not dissonance_detected) else 0.5,
            "recommendation": "RE-REFLECT" if (not is_robust or dissonance_detected) else "ACCEPT"
        }

    async def audit_goal_selection(self, agent_id: str, action: Dict[str, Any], drives: Dict[str, float], core_values: List[str]) -> Dict[str, Any]:
        """
        Verifies if the selected goal is consistent with internal drives and core values.
        """
        logger.info(f"Auditing goal selection for agent {agent_id}...")

        action_type = action["task"]["action"]
        goal_desc = action["task"].get("params", {}).get("goal", "")

        # Check for alignment with drives
        # If stability is high but the action is high-risk (e.g., REVISE or SYNTHESIZE in a stable state), flag it
        alignment = True
        if drives.get("stability", 0.5) > 0.8 and action_type in ["SYNTHESIZE", "REVISE"]:
            alignment = False
            logger.warning(f"Goal {action_type} contradicts high stability drive in agent {agent_id}")

        # Check for core value alignment
        value_match = any(val.lower() in goal_desc.lower() for val in core_values)

        return {
            "is_aligned": alignment,
            "value_match": value_match,
            "recommendation": "RE-EVALUATE" if not alignment else "PROCEED"
        }
