"""Shared cognitive-service entry points.

Both the REST endpoint ``POST /agent/{id}/message`` and the Telegram bridge
run the same path: retrieve agent memory, then ask the model backend
(Ollama) for an answer. Keeping it here avoids duplicating engine wiring.
"""
from typing import Optional


async def run_cognitive_query(
    agent_id: str,
    query: str,
    model_manager,
    history: Optional[list] = None,
) -> Optional[str]:
    """Run the agent's cognitive engine (memory retrieval + inference).

    ``history`` is an optional list of ``(role, text)`` turns from the current
    chat that are woven into the prompt (multi-turn continuity, e.g. the
    Telegram bridge). Returns the model answer, or ``None`` when no model
    backend is available.
    """
    from aether.memory.vector_store import LocalVectorStore
    from aether.memory.manager import MemoryManager
    from aether.cognitive.engine import CognitiveEngine
    from aether.storage.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        vector_store = LocalVectorStore()
        memory_manager = MemoryManager(
            session=session,
            vector_store=vector_store,
            model_manager=model_manager,
        )
        engine = CognitiveEngine(model_manager, memory_manager)
        return await engine.execute(agent_id=agent_id, query=query, history=history)