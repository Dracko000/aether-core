import pytest
import asyncio
import time
from aether.storage.database import AsyncSessionLocal, engine
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_relationships import RelationshipRepository
from aether.storage.repositories_collective import CollectiveRepository
from aether.memory.beliefs import BeliefManager
from aether.cognitive.social import SocialResolver
from aether.storage.models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
async def test_trust_weighted_integration():
    """Verify that knowledge transfer is weighted by the trust relationship between agents."""
    await init_db()
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        rel_repo = RelationshipRepository(session)
        belief_mgr = BeliefManager(session)
        resolver = SocialResolver(session, belief_mgr)

        alice = "agent_alice"
        bob = "agent_bob"
        await agent_repo.create(alice)
        await agent_repo.create(bob)

        # Scenario 1: High Trust
        await rel_repo.set_relationship(bob, alice, trust=0.9)
        fragment = {"content": "The core is stable", "confidence": 0.8}

        result = await resolver.resolve_knowledge_transfer(bob, alice, fragment)
        assert result["action"] == "CREATE"
        assert result["confidence"] == pytest.approx(0.72)

        # Scenario 2: Low Trust
        await rel_repo.set_relationship(bob, alice, trust=0.2)
        result = await resolver.resolve_knowledge_transfer(bob, alice, fragment)
        assert result["confidence"] == pytest.approx(0.16)

@pytest.mark.asyncio
async def test_social_conflict_resolution():
    """Verify conflict resolution logic when contradictory knowledge is transferred."""
    await init_db()
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        rel_repo = RelationshipRepository(session)
        belief_mgr = BeliefManager(session)
        resolver = SocialResolver(session, belief_mgr)

        bob = "agent_bob"
        alice = "agent_alice"
        await agent_repo.create(bob)
        await agent_repo.create(alice)

        # Baseline belief
        await belief_mgr.update_or_create_belief(bob, "The sky is blue", 0.8)

        # Scenario A: Low trust contradictory information
        await rel_repo.set_relationship(bob, alice, trust=0.3)
        fragment_contradict = {"content": "The sky is not blue, it is green", "confidence": 0.9}

        result = await resolver.resolve_knowledge_transfer(bob, alice, fragment_contradict)
        assert result["action"] == "IGNORE"

        # Scenario B: High trust contradictory information
        await rel_repo.set_relationship(bob, alice, trust=0.95)
        result = await resolver.resolve_knowledge_transfer(bob, alice, fragment_contradict)
        assert result["action"] == "OVERRIDE"
        assert "green" in result["content"]

@pytest.mark.asyncio
async def test_coalition_formation():
    """Verify the mechanism for forming agent coalitions around shared objectives."""
    await init_db()
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        from aether.cognitive.coalitions import CoalitionManager
        coal_mgr = CoalitionManager(session)

        leader = "leader_01"
        await agent_repo.create(leader)

        coalition_id = await coal_mgr.form_coalition(leader, "goal_shared_01", ["coding", "research"])

        members = await coal_mgr.get_coalition_members(coalition_id)
        assert leader in members
        assert "coal_" in coalition_id
