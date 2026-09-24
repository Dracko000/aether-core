from fastapi.testclient import TestClient

from aether.api.app import app

client = TestClient(app)


def test_models_list():
    """Capability matrix is exposed via GET /models."""
    response = client.get("/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    assert len(models) >= 5
    ids = {m["model_id"] for m in models}
    assert "llama3" in ids and "llama3:70b" in ids
    expert = next(m for m in models if m["model_id"] == "llama3:70b")
    assert expert["reasoning_level"] == 3


def test_models_select_expert():
    """GET /models/select returns the most capable fitting model."""
    response = client.get("/models/select", params={"reasoning_level": 2, "max_context": 8192})
    assert response.status_code == 200
    body = response.json()
    assert body["model_id"] in {"mistral", "deepseek-r1:7b", "llama3:70b"}
    assert body["reasoning_level"] >= 2


def test_models_select_fallback_to_default():
    """Unmeetable requirements fall back to the configured default model."""
    response = client.get("/models/select", params={"reasoning_level": 3, "max_context": 200000})
    assert response.status_code == 200
    assert response.json()["model_id"] == "llama3"