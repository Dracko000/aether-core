from typing import Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from aether.storage.repositories_drives import DriveRepository
from aether.storage.models_drives import AgentDriveModel

logger = logging.getLogger("aether.cognitive.emotions")

class EmotionManager:
    """
    Manages the affective state of agents and modulates cognitive drives.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DriveRepository(session)

    async def update_emotion(self, agent_id: str, emotion: str, delta: float):
        """
        Adjusts a specific emotional state.
        Valid emotions: frustration, satisfaction, anxiety, joy.
        """
        drives = await self.repo.get_drives(agent_id)
        if not drives:
            # Initialize default drives and emotions if none exist yet
            drives = {
                "curiosity": 0.5,
                "coherence": 0.5,
                "stability": 0.5,
                "frustration": 0.0,
                "satisfaction": 0.0,
                "anxiety": 0.0,
                "joy": 0.0,
            }

        current_val = drives.get(emotion, 0.0)
        new_val = max(0.0, min(1.0, current_val + delta))
        
        # Update only the specific emotion field
        updated_drives = {**drives, emotion: new_val}
        await self.repo.update_drives(agent_id, updated_drives)
        logger.info(f"Agent {agent_id} emotion {emotion} updated: {current_val:.2f} -> {new_val:.2f}")

    async def decay_emotions(self, agent_id: str):
        """
        Gradually returns emotional states toward zero (neutrality).
        """
        drives = await self.repo.get_drives(agent_id)
        if not drives: return

        emotions = ["frustration", "satisfaction", "anxiety", "joy"]
        updated = False
        new_drives = drives.copy()

        for e in emotions:
            val = drives.get(e, 0.0)
            if val > 0:
                new_drives[e] = max(0.0, val - 0.05)
                updated = True
        
        if updated:
            await self.repo.update_drives(agent_id, new_drives)
            logger.debug(f"Emotional decay applied to agent {agent_id}")

    def get_emotion_modifier(self, drives: Dict[str, float], drive_type: str) -> float:
        """
        Returns a multiplier for a specific drive based on current emotional states.
        Positive emotions (joy, satisfaction) boost priority -> lower weight.
        Negative emotions (frustration, anxiety) reduce priority -> higher weight.
        Formula: 1.0 + (Negative_Modulators - Positive_Modulators)
        """
        modifier = 1.0
        
        if drive_type == "curiosity":
            modifier -= drives.get("joy", 0.0) * 0.5
            modifier += drives.get("frustration", 0.0) * 0.3
        elif drive_type == "coherence":
            modifier -= drives.get("satisfaction", 0.0) * 0.2
            modifier += drives.get("anxiety", 0.0) * 0.4
        elif drive_type == "stability":
            modifier -= drives.get("anxiety", 0.0) * 0.6
            modifier += drives.get("joy", 0.0) * 0.2
            
        return max(0.5, min(2.0, modifier))
