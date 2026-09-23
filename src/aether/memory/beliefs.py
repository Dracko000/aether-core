from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from aether.storage.repositories_beliefs import BeliefRepository
from aether.storage.models_beliefs import BeliefModel

class BeliefManager:
    """
    Manages the cognitive belief layer, providing a high-level API for the reflection cycle.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BeliefRepository(session)

    async def get_strongest_beliefs(self, agent_id: str, limit: int = 10, min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        beliefs = await self.repo.get_beliefs(agent_id, min_confidence=min_confidence)
        return [
            {
                "belief_id": b.belief_id,
                "content": b.content,
                "confidence": b.confidence
            } for b in beliefs[:limit]
        ]

    async def update_or_create_belief(self, agent_id: str, content: str, confidence_delta: float, source_ids: Optional[List[str]] = None) -> str:
        """
        Updates an existing belief based on new evidence or initializes a new belief.
        Implements confidence adjustment: confidence = clamp(confidence + delta, 0, 1).
        """
        # Identify similar beliefs via content analysis
        beliefs = await self.repo.get_beliefs(agent_id)
        existing_belief = None
        for b in beliefs:
            # Broaden match for comprehensive coverage
            # Implement robust similarity check for contradictions
            # If the content is very different but shares key words, it might be a contradiction
            if content.lower() in b.content.lower() or b.content.lower() in content.lower():
                existing_belief = b
                break

        # Identify explicitly contradicted beliefs to allow SocialResolver handling.
        if not existing_belief:
            for b in beliefs:
                # HEURISTIC: Match subject via consecutive word sequences
                b_words = b.content.lower().split()
                c_words = content.lower().split()

                for i in range(min(len(b_words), len(c_words)) - 2):
                    if b_words[i:i+3] == c_words[i:i+3]:
                        existing_belief = b
                        break
                if existing_belief: break

        if existing_belief:
            new_conf = max(0.0, min(1.0, existing_belief.confidence + confidence_delta))
            await self.repo.update_belief(existing_belief.belief_id, new_conf)
            return existing_belief.belief_id
        else:
            import uuid
            belief_id = f"belief_{uuid.uuid4().hex[:8]}"
            # Initialize new belief with delta applied to base confidence of 0.5
            await self.repo.create_belief(belief_id, agent_id, content, max(0.0, min(1.0, 0.5 + confidence_delta)), source_ids)
            return belief_id
