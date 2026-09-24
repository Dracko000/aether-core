"""Integration tests for the /setup auto-setup page and env helper utilities."""
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from aether.api.app import app
from aether.api.routes import setup as setup_mod
from aether.config import settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def _restore_settings():
    saved = (
        settings.TELEGRAM_BOT_TOKEN,
        settings.TELEGRAM_AGENT_ID,
        settings.TELEGRAM_ENABLED,
        settings.OLLAMA_MODEL,
    )
    yield
    (
        settings.TELEGRAM_BOT_TOKEN,
        settings.TELEGRAM_AGENT_ID,
        settings.TELEGRAM_ENABLED,
        settings.OLLAMA_MODEL,
    ) = saved


# ------------------------------------------------------------ env utilities
def test_load_write_env_roundtrip(tmp_path):
    env = tmp_path / ".env"
    setup_mod.write_env({"A": "1", "B": "2"}, env)
    assert setup_mod.load_env(env) == {"A": "1", "B": "2"}
    # merge preserves unrelated keys
    setup_mod.write_env({"B": "22"}, env)
    assert setup_mod.load_env(env) == {"A": "1", "B": "22"}
    # comments and blanks are ignored
    env.write_text("# comment\n\nK=V\n")
    assert setup_mod.load_env(env) == {"K": "V"}


# ------------------------------------------------------------- validators
class _FakeResp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    @property
    def text(self):
        return ""


class _FakeClient:
    def __init__(self, *a, **k):
        self._resp = _FakeResp(
            {"ok": True, "result": {"username": "my_aether_bot", "first_name": "Aether"}}
        )
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        urls = getattr(self, "urls", None)
        if urls is not None:
            urls.append(url)
        return self._resp


@pytest.mark.asyncio
async def test_check_telegram_token_ok(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(setup_mod.httpx, "AsyncClient", lambda *a, **k: fake)
    info = await setup_mod.check_telegram_token("123:TEST")
    assert info["ok"] is True
    assert info["username"] == "my_aether_bot"
    assert any("/bot123:TEST/getMe" in u for u in fake.urls)


@pytest.mark.asyncio
async def test_check_telegram_token_rejected(monkeypatch):
    class Bad(_FakeClient):
        def __init__(self, *a, **k):
            self._resp = _FakeResp({"ok": False, "description": "Unauthorized"})

    monkeypatch.setattr(setup_mod.httpx, "AsyncClient", Bad)
    info = await setup_mod.check_telegram_token("123:BAD")
    assert info["ok"] is False
    assert "Unauthorized" in info["detail"]


@pytest.mark.asyncio
async def test_check_ollama_ok(monkeypatch):
    class O(_FakeClient):
        def __init__(self, *a, **k):
            self._resp = _FakeResp({"models": [{"name": "llama3"}]})

    monkeypatch.setattr(setup_mod.httpx, "AsyncClient", O)
    info = await setup_mod.check_ollama("http://localhost:11434")
    assert info["ok"] is True
    assert info["models"] == ["llama3"]


# ------------------------------------------------------------------- page
def test_setup_page_renders():
    resp = client.get("/setup")
    assert resp.status_code == 200
    assert "BotFather" in resp.text
    assert "Save &amp; Start Bot" in resp.text


def test_setup_status_endpoint():
    resp = client.get("/setup/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "bot_running" in body
    assert "agent_id" in body


def test_setup_stop_action_is_safe(monkeypatch, tmp_path):
    monkeypatch.setenv("AETHER_ENV_FILE", str(tmp_path / ".env"))
    resp = client.post("/setup", json={"action": "stop"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["bot_running"] is False
    assert (tmp_path / ".env").exists()
    assert setup_mod.load_env(tmp_path / ".env")["TELEGRAM_ENABLED"] == "false"


def test_setup_start_missing_token(monkeypatch, tmp_path):
    monkeypatch.setenv("AETHER_ENV_FILE", str(tmp_path / ".env"))
    resp = client.post("/setup", json={"action": "start", "telegram_token": ""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "token is required" in body["error"]


def test_setup_start_writes_env_and_starts(monkeypatch, tmp_path):
    monkeypatch.setenv("AETHER_ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.setattr(
        setup_mod, "check_telegram_token", AsyncMock(return_value={"ok": True, "username": "my_bot"})
    )
    started = AsyncMock()
    monkeypatch.setattr(setup_mod, "start_bot_in_app", started)

    resp = client.post(
        "/setup",
        json={
            "action": "start",
            "telegram_token": "123:TEST",
            "agent_id": "neo",
            "ollama_model": "qwen2.5:0.5b",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["agent_id"] == "neo"
    started.assert_awaited_once()

    env = setup_mod.load_env(tmp_path / ".env")
    assert env["TELEGRAM_BOT_TOKEN"] == "123:TEST"
    assert env["TELEGRAM_AGENT_ID"] == "neo"
    assert env["TELEGRAM_ENABLED"] == "true"
    assert env["OLLAMA_MODEL"] == "qwen2.5:0.5b"

    # In-process singleton reflects the new token immediately.
    assert settings.TELEGRAM_BOT_TOKEN == "123:TEST"
    assert settings.TELEGRAM_AGENT_ID == "neo"
    assert settings.TELEGRAM_ENABLED is True


def test_setup_start_rejected_token(monkeypatch, tmp_path):
    monkeypatch.setenv("AETHER_ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.setattr(
        setup_mod,
        "check_telegram_token",
        AsyncMock(return_value={"ok": False, "detail": "Unauthorized"}),
    )
    resp = client.post("/setup", json={"action": "start", "telegram_token": "123:NO"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
    assert "Unauthorized" in resp.json()["error"]
    # Nothing written to env on failure.
    assert not (tmp_path / ".env").exists() or "TELEGRAM_BOT_TOKEN" not in setup_mod.load_env(
        tmp_path / ".env"
    )