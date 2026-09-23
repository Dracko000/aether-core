from typing import List, Dict, Any
from pydantic import BaseModel

class MemoryExtraction(BaseModel):
    facts: List[str]
    lessons: List[str]
    importance_score: float # 0.0 to 1.0

class MemoryExtractor:
    """
    Transforms raw experience data into distilled memory representations.
    Utilizes language models to extract salient facts and durable lessons.
    """
    def __init__(self, model_manager):
        self.model_manager = model_manager

    async def extract(self, agent_id: str, experience: Dict[str, Any]) -> MemoryExtraction:
        prompt = (
            f"Analyze the following experience for agent {agent_id}:\n"
            f"Event: {experience.get('event')}\n"
            f"Context: {experience.get('context')}\n"
            f"Result: {experience.get('result')}\n\n"
            "Extract key facts and a durable lesson. Rate the importance (0.0 to 1.0)."
        )

        # In production, ModelManager.request() is used with a structured schema.
        # The following block represents the structured call logic:
        # result = await self.model_manager.request(5, lambda: self.model_manager.adapter.structured(
        #     [{"role": "user", "content": prompt}], MemoryExtraction
        # ))

        # Temporary mock implementation for current development phase.
        return MemoryExtraction(
            facts=["The user prefers concise reports"],
            lessons=["Always validate the environment before deployment"],
            importance_score=0.8
        )
