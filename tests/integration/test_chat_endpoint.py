import pytest
from fastapi.testclient import TestClient

from aether.api.app import app, MessageRequest, send_message
from aether.storage.database import init_db
from aether.model.manager import ModelManager
from aether.model.mock import MockAdapter

client = TestClient(app)


@pytest.mark.asyncio
async def test_agent_message_flows_through_engine():
    """Sending a message to an agent produces an engine answer via the model backend."""
    await init_db()

    # Inject a mock model backend. ModelManager's worker task lives on the
    # current event loop, so we invoke the endpoint function directly (same
    # loop) rather than through TestClient — its separate portal loop would
    # deadlock on the cross-loop asyncio Future.
    manager = ModelManager(MockAdapter())
    app.state.model_manager = manager
    try:
        client.post(
            "/agents/",
            json={
                "agent_id": "aria_chat_001",
                "name": "Aria",
                "role": "Researcher",
                "personality": {"trait": "analytical"},
                "skills": ["research"],
            },
        )

        resp = await send_message(
            "aria_chat_001",
            MessageRequest(
                sender_id="user_test",
                content="Hello Aria, please summarize the current system status report for me",
            ),
        )
        assert resp["status"] == "sent"
        assert resp["receiver_id"] == "aria_chat_001"
        # Engine ran the slow path -> adapter.generate() -> mock answer.
        assert resp["response"] == "Mock response to generate"
    finally:
        await manager.shutdown()
        app.state.model_manager = None


def test_message_without_model_backend_still_sends():
    """Without a started model backend the message is still persisted and delivered."""
    assert getattr(app.state, "model_manager", None) is None
    client.post(
        "/agents/",
        json={
            "agent_id": "aria_chat_002",
            "name": "Aria-2",
            "role": "Researcher",
            "personality": {"trait": "analytical"},
            "skills": ["research"],
        },
    )
    resp = client.post(
        "/agent/aria_chat_002/message",
        json={"sender_id": "user_test", "content": "ping"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sent"
    assert body["response"] is None