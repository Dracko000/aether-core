from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from aether.storage.repositories_drives import DriveRepository

logger = logging.getLogger("aether.cognitive.drives")

class DriveManager:
    """
    Manages the cognitive drives that motivate agent behavior.
    Drives dynamically weight goal priorities based on environmental stimuli.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DriveRepository(session)

    async def update_drives(self, agent_id: str, event_type: str, impact: Dict[str, float]):
        """
        Adjusts drive levels based on an event.
        Impact map specifies how much each drive increases or decreases.
        Example impact: {"curiosity": 0.1, "coherence": -0.05}
        """
        current_drives = await self.repo.get_drives(agent_id) or {
            "curiosity": 0.5,
            "coherence": 0.5,
            "stability": 0.5
        }

        new_drives = {}
        for drive, val in current_drives.items():
            change = impact.get(drive, 0.0)
            # Clamp values between 0.0 and 1.0
            new_drives[drive] = max(0.0, min(1.0, val + change))

        await self.repo.update_drives(agent_id, new_drives)
        logger.info(f"Updated drives for agent {agent_id} after {event_type}: {new_drives}")

    def calculate_priority_weight(self, goal_type: str, drives: Dict[str, float]) -> float:
        """
        Calculates a priority multiplier based on the alignment between
        the goal's nature and the agent's current drives, modulated by emotions.
        """
        # Mapping goal keywords to drives
        weights = {
            "curiosity": ["research", "explore", "discover", "learn", "search"],
            "coherence": ["resolve", "contradiction", "synthesize", "verify", "critique"],
            "stability": ["complete", "execute", "maintain", "stabilize", "finalize"]
        }

        # Default weight is 1.0
        final_weight = 1.0

        # Check if goal matches any drive keywords
        for drive, keywords in weights.items():
            if any(kw in goal_type.lower() for kw in keywords):
                # 1. Base Drive Weight
                # Higher drive = lower numeric priority (more important)
                base_weight = (1.1 - drives.get(drive, 0.5))

                # 2. Emotional Modulation
                # We import EmotionManager inside to avoid circular imports
                from aether.cognitive.emotions import EmotionManager
                # We use a dummy session or pass one in.
                # Since this is a pure calculation, we can pass the modifier externally
                # or calculate it here if we have the drives dict.

                # Internal modulation logic (mirrors EmotionManager.get_emotion_modifier)
                # Positive emotions (joy, satisfaction) boost priority -> lower weight.
                # Negative emotions (frustration, anxiety) reduce priority -> higher weight.
                modifier = 1.0
                if drive == "curiosity":
                    modifier -= drives.get("joy", 0.0) * 0.5
                    modifier += drives.get("frustration", 0.0) * 0.3
                elif drive == "coherence":
                    modifier -= drives.get("satisfaction", 0.0) * 0.2
                    modifier += drives.get("anxiety", 0.0) * 0.4
                elif drive == "stability":
                    modifier -= drives.get("anxiety", 0.0) * 0.6
                    modifier += drives.get("joy", 0.0) * 0.2

                final_weight *= (base_weight * max(0.5, min(2.0, modifier)))

        return final_weight
