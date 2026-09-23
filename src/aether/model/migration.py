import logging
import uuid
from typing import Dict, Any, Optional
from aether.agent.runtime import AgentRuntime
from aether.storage.database import AsyncSessionLocal
from aether.storage.repositories import AgentRepository
from aether.storage.repositories_evolution import EvolutionRepository
from aether.model.translator import MemoryTranslator

logger = logging.getLogger("aether.model.migration")

class ModelMigrationManager:
    """
    Handles the transition of an agent from one model version to another,
    ensuring identity continuity and memory compatibility.
    """
    def __init__(self, runtime: AgentRuntime, capability_matrix):
        self.runtime = runtime
        self.capability_matrix = capability_matrix

    async def migrate_agent(self, agent_id: str, target_model_id: str):
        """
        Migrates an agent to a target model version while maintaining identity continuity
        and memory compatibility.
        """
        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            evo_repo = EvolutionRepository(session)

            agent = await agent_repo.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            from_model_id = agent.model_id

            # 1. Validate target model capabilities
            target_caps = self.capability_matrix.get_capabilities(target_model_id)
            if not target_caps:
                raise ValueError(f"Target model {target_model_id} not registered in Capability Matrix")

            # 2. Log migration start
            logger.info(f"Migrating agent {agent_id} from {from_model_id} to {target_model_id}")

            # 3. Cognitive Translation (Memory Re-Synthesis)
            from aether.memory.manager import MemoryManager
            from aether.memory.vector_store import LocalVectorStore

            # Initialize translator with a systemic vector store
            mem_mgr = MemoryManager(session, LocalVectorStore())
            translator = MemoryTranslator(session, mem_mgr)

            await translator.translate_all(agent_id, target_model_id)

            # 4. Update agent record
            agent.model_id = target_model_id
            await session.commit()

            # 5. Record evolution history
            await evo_repo.record_migration(
                migration_id=str(uuid.uuid4()),
                agent_id=agent_id,
                from_model=from_model_id,
                to_model=target_model_id,
                status="SUCCESS",
                notes="Completed cognitive translation and identity bridge."
            )

            # 6. Handle runtime update
            if self.runtime.is_agent_awake(agent_id):
                logger.info(f"Refreshing active agent {agent_id} for new model")
                # Clear L1 Working Memory and force re-load from L2/L3 based on target model context preferences.

            logger.info(f"Agent {agent_id} successfully evolved to {target_model_id}")
            return True
