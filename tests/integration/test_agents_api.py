import pytest
from fastapi.testclient import TestClient
from aether.api.app import app
from aether.storage.database import init_db

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_agent_endpoint():
    await init_db()

    payload = {
        "agent_id": "aria_001",
        "name": "Aria",
        "role": "Researcher",
        "personality": {"trait": "analytical"},
        "skills": ["research"]
    }

    response = client.post("/agents/", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["agent_id"] == "aria_001"
