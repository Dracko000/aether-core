from typing import List, Dict, Any, Optional
from aether.memory.vector_store import LocalVectorStore
from aether.memory.embeddings import EmbeddingModel
from aether.memory.working import WorkingMemory
from aether.memory.episodic import EpisodicMemory
from aether.memory.semantic import SemanticMemory
from aether.memory.procedural import ProceduralMemory
from aether.memory.longterm import LongTermMemory
from sqlalchemy.ext.asyncio import AsyncSession

class MemoryManager:
    """
    Orchestrates retrieval across the five memory tiers.
    """
    def __init__(self, session: AsyncSession, vector_store: LocalVectorStore):
        self.session = session
        self.vector_store = vector_store
        self.embeddings = EmbeddingModel()

        # Initialize tiers
        self.l1 = WorkingMemory()
        self.l2 = EpisodicMemory(session)
        self.l3 = SemanticMemory(session)
        self.l4 = ProceduralMemory(session)
        self.l5 = LongTermMemory(session)

    async def retrieve(self, agent_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # 1. Generate embedding for the query
        query_vec = self.embeddings.embed(query)

        # 2. Vector search across semantic/longterm memories
        # In this MVP, metadata in vector_store tells us which tier it belongs to
        vector_results = await self.vector_store.search(query_vec, top_k=top_k)

        # 3. Filter vector results for this specific agent
        agent_memories = [res for res in vector_results if res[1].get("agent_id") == agent_id]

        # 4. Combine with recent episodic memories (L2)
        episodic = await self.l2.get_recent(agent_id, limit=5)

        # 5. Assembly: Combine and return as a list of context snippets
        context = []
        for score, meta in agent_memories:
            context.append({"type": "semantic", "content": meta.get("content", ""), "score": score})

        for entry in episodic:
            context.append({"type": "episodic", "content": entry["event"], "score": 1.0})

        return context

    async def add_to_semantic(self, agent_id: str, fact: str, importance: float):
        # Save to SQLite
        await self.l3.add(agent_id, fact, importance)
        # Save to Vector Store for retrieval
        vec = self.embeddings.embed(fact)
        await self.vector_store.add(vec, {"agent_id": agent_id, "content": fact, "tier": "L3"}, f"{agent_id}_sem_{hash(fact)}")
