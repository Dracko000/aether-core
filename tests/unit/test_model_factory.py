import pytest
import asyncio

from aether.config import settings
from aether.model.capabilities import CapabilityMatrix
from aether.model.factory import (
    build_adapter,
    build_model_manager,
    create_default_capability_matrix,
    register_default_models,
    select_model_for,
)
from aether.model.ollama import OllamaAdapter


def test_build_adapter_uses_config_defaults():
    """Production adapter is an Ollama backend wired from settings."""
    adapter = build_adapter()
    assert isinstance(adapter, OllamaAdapter)
    assert adapter.base_url == settings.OLLAMA_BASE_URL
    assert adapter.model_name == settings.OLLAMA_MODEL


def test_register_default_models_populates_matrix():
    matrix = create_default_capability_matrix()
    assert len(matrix.all_models()) >= 5
    # Expert tier
    assert matrix.find_best_model({"reasoning_level": 3, "max_context": 8192}) == "llama3:70b"
    # Large context window → qwen2.5:7b (only registered model with 32k ctx)
    assert matrix.find_best_model({"reasoning_level": 1, "max_context": 32768}) == "qwen2.5:7b"


def test_select_model_for_falls_back_to_configured_default():
    """Requirement no registered model meets → configured default, if registered."""
    # llama3:70b has max_context 8192 < 200000, so nothing matches.
    result = select_model_for({"reasoning_level": 3, "max_context": 200000})
    assert result == settings.OLLAMA_MODEL  # "llama3" is registered → fallback


def test_select_model_for_raises_when_default_unregistered(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "custom-unknown-model")
    with pytest.raises(ValueError, match="not registered"):
        select_model_for({"reasoning_level": 3, "max_context": 200000})


def test_register_default_models_in_place():
    matrix = CapabilityMatrix()
    register_default_models(matrix)
    assert matrix.get_capabilities("mistral") is not None
    assert matrix.get_capabilities("mistral").reasoning_level == 2


@pytest.mark.asyncio
async def test_build_model_manager_uses_ollama_adapter():
    manager = build_model_manager()
    try:
        assert isinstance(manager.adapter, OllamaAdapter)
    finally:
        await manager.shutdown()