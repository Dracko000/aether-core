from typing import List, Dict, Any
from pydantic import BaseModel

class MemoryExtraction(BaseModel):
    facts: List[str]
    lessons: List[str]
    importance_score: float # 0.0 to 1.0

class MemoryExtractor:
    """
    Logic for transforming raw experiences into distilled memories.
    Uses the LLM to extract meaningful facts and lessons.
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

        # In a real scenario, we'd use ModelManager.request() with a structured schema
        # For the MVP's logic, we simulate the structured call:
        # result = await self.model_manager.request(5, lambda: self.model_manager.adapter.structured(
        #     [{"role": "user", "content": prompt}], MemoryExtraction
        # ))

        # Mocking the extraction for now since we are in the middle of Plan 4
        return MemoryExtraction(
            facts=["The user prefers concise reports"],
            lessons=["Always validate the environment before deployment"],
            importance_score=0.8
        )
