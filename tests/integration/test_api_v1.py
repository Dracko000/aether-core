import pytest
import asyncio
import uuid
from httpx import ASGITransport, AsyncClient
from aether.api.app import app
from aether.storage.database import AsyncSessionLocal, init_db
from aether.storage.repositories import AgentRepository, IdentityRepository

@pytest.mark.asyncio
async def test_api_lifecycle_flow():
    """Verify the agent lifecycle via REST API endpoints."""
    agent_id = "api_test_agent"

    async with AsyncSessionLocal() as session:
        await init_db()
        agent_repo = AgentRepository(session)
        id_repo = IdentityRepository(session)
        await agent_repo.create(agent_id)
        await id_repo.create(agent_id, "API Agent", "Tester", {}, [])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Activation
        resp = await client.post(f"/agent/{agent_id}/wake")
        assert resp.status_code == 200
        assert resp.json()["status"] == "awakened"

        # 2. State Verification
        resp = await client.get(f"/agent/{agent_id}/state")
        assert resp.status_code == 200
        assert resp.json()["state"] == "AWAKENED"

        # 3. Goal Specification
        resp = await client.post(f"/agent/{agent_id}/goals", json={"description": "Test goal", "priority": 1})
        assert resp.status_code == 200
        assert "goal_id" in resp.json()

        # 4. Deactivation
        resp = await client.post(f"/agent/{agent_id}/sleep")
        assert resp.status_code == 200
        assert resp.json()["status"] == "sleeping"

        # 5. Persistence Verification
        resp = await client.get(f"/agent/{agent_id}/state")
        assert resp.json()["state"] == "SLEEPING"
