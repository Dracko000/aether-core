from typing import List, Dict, Any, Optional
from aether.memory.vector_store import LocalVectorStore
from aether.memory.embeddings import EmbeddingModel
from aether.memory.working import WorkingMemory
from aether.memory.episodic import EpisodicMemoryManager
from aether.memory.semantic import SemanticMemory
from aether.memory.procedural import ProceduralMemory
from aether.memory.longterm import LongTermMemoryManager
from aether.memory.extraction import MemoryExtractor
from aether.memory.importance import ImportanceScorer
from aether.storage.repositories_experience import ExperienceGraphRepository
from sqlalchemy.ext.asyncio import AsyncSession

class MemoryManager:
    """
    Orchestrates memory retrieval and consolidation across the five cognitive tiers.
    """
    def __init__(self, session: AsyncSession, vector_store: LocalVectorStore, model_manager=None):
        self.session = session
        self.vector_store = vector_store
        self.embeddings = EmbeddingModel()
        self.model_manager = model_manager

        # Initialize tiers
        self.l1 = WorkingMemory()
        self.l2 = EpisodicMemoryManager(session)
        self.l3 = SemanticMemory(session)
        self.l4 = ProceduralMemory(session)
        self.l5 = LongTermMemoryManager(session)
        self.graph = ExperienceGraphRepository(session)

        self.extractor = MemoryExtractor(model_manager)
        self.scorer = ImportanceScorer()

    async def retrieve(self, agent_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # 1. Compute query embedding
        query_vec = self.embeddings.embed(query)

        # 2. Perform vector search across semantic and long-term tiers
        vector_results = await self.vector_store.search(query_vec, top_k=top_k)

        # 3. Filter results by agent identifier
        agent_memories = [res for res in vector_results if res[1].get("agent_id") == agent_id]

        # 4. Integrate recent episodic memories (L2)
        episodic = await self.l2.get_recent(agent_id, limit=5)

        # 5. Context assembly
        context = []
        for score, meta in agent_memories:
            context.append({"type": "semantic", "content": meta.get("content", ""), "score": score})

        for entry in episodic:
            # Entry is a model instance
            context.append({"type": "episodic", "content": entry.event, "score": 1.0})

        return context

    async def retrieve_associative(self, agent_id: str, start_node_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Traverse the experience graph to find related memories.
        """
        results = []
        visited = set()
        queue = [(start_node_id, 0)]

        while queue:
            node_id, current_depth = queue.pop(0)
            if node_id in visited or current_depth > depth:
                continue

            visited.add(node_id)
            node = await self.graph.get_node(node_id)
            if node:
                results.append({"type": "experience", "content": node.content, "id": node.node_id})

                # Add neighbors to queue
                neighbors = await self.graph.get_neighbors(node_id)
                for neighbor in neighbors:
                    queue.append((neighbor.node_id, current_depth + 1))

        return results

    async def consolidate(self, agent_id: str, experience: Dict[str, Any]):
        """
        The Consolidation Pipeline: Experience -> Extraction -> Score -> Tiered Storage.
        """
        # 1. Extract salient facts and lessons
        extraction = await self.extractor.extract(agent_id, experience)

        # Integration: Formal Reflection Cycle
        # Execute formal reflection instead of simple extraction
        from aether.cognitive.reflection import ReflectionCycle
        from aether.memory.beliefs import BeliefManager

        reflection = ReflectionCycle(self.session, self, BeliefManager(self.session))
        reflection_result = await reflection.reflect(agent_id, experience)

        # Use the synthesis from reflection as the primary lesson for episodic memory
        lesson = reflection_result["synthesis"].get("lesson", extraction.lessons[0] if extraction.lessons else None)
        # -------------------------------------------


        # 2. Process extracted facts
        for fact in extraction.facts:
            # Calculate importance
            importance = self.scorer.calculate(extraction.importance_score, recurrence=1, goal_alignment=True)

            # 3. Assign storage tier based on importance
            if importance > 0.9:
                await self.l5.add(agent_id, fact, importance)
            elif importance > 0.6:
                await self.l3.add(agent_id, fact, importance)

            # Persist to vector store for semantic retrieval
            vec = self.embeddings.embed(fact)
            await self.vector_store.add(vec, {"agent_id": agent_id, "content": fact, "tier": "semantic"}, f"{agent_id}_sem_{hash(fact)}")

        # Store raw experience in Episodic Memory (L2)
        await self.l2.add(
            agent_id,
            experience.get("event", ""),
            experience.get("context", ""),
            experience.get("result", ""),
            extraction.lessons[0] if extraction.lessons else None
        )
