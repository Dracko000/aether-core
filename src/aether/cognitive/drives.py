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
        the goal's nature and the agent's current drives.
        """
        # Mapping goal keywords to drives
        weights = {
            "curiosity": ["research", "explore", "discover", "learn", "search"],
            "coherence": ["resolve", "contradiction", "synthesize", "verify", "critique"],
            "stability": ["complete", "execute", "maintain", "stabilize", "finalize"]
        }

        # Default weight is 1.0
        final_weight = 1.0

        # Check if goal matches any drive keywords (simulated match for now)
        # In a real system, goals would have explicit 'type' tags.
        for drive, keywords in weights.items():
            # We assume goal_type is the description or a tag
            if any(kw in goal_type.lower() for kw in keywords):
                # Multiply by the drive level (0.0 - 1.0).
                # Higher drive = higher weight = lower numeric priority value.
                # We subtract the drive from 1.0 because low priority value = high importance.
                final_weight *= (1.1 - drives.get(drive, 0.5))

        return final_weight
