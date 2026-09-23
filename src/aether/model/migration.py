import logging
from typing import Dict, Any, Optional
from aether.agent.runtime import AgentRuntime
from aether.storage.database import AsyncSessionLocal
from aether.storage.repositories import AgentRepository

logger = logging.getLogger("aether.model.migration")

class ModelMigrationManager:
    """
    Handles the transition of an agent from one model version to another.
    """
    def __init__(self, runtime: AgentRuntime, capability_matrix):
        self.runtime = runtime
        self.capability_matrix = capability_matrix

    async def migrate_agent(self, agent_id: str, target_model_id: str):
        """
        Performs a safe migration of an agent to a new model.
        """
        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            agent = await agent_repo.get(agent_id)
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # 1. Validate target model capabilities
            target_caps = self.capability_matrix.get_capabilities(target_model_id)
            if not target_caps:
                raise ValueError(f"Target model {target_model_id} not registered in Capability Matrix")

            # 2. Log migration event
            logger.info(f"Migrating agent {agent_id} from {agent.model_id} to {target_model_id}")
            
            # 3. Update agent record
            agent.model_id = target_model_id
            await session.commit()

            # 4. Handle runtime update
            if self.runtime.is_agent_awake(agent_id):
                # If awake, we need to refresh the identity and context to match new model's prompt requirements
                logger.info(f"Refreshing active agent {agent_id} for new model")
                # In a full implementation, this would trigger a re-synthesis of the Working Memory (L1)
                # to fit the new model's context window or formatting preferences.
                
            logger.info(f"Agent {agent_id} successfully migrated to {target_model_id}")
            return True
