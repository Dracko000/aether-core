import pytest
import asyncio
from aether.model.manager import ModelManager
from aether.model.mock import MockAdapter
from aether.model.ollama import OllamaAdapter
from pydantic import BaseModel

class SimpleSchema(BaseModel):
    answer: str

@pytest.mark.asyncio
async def test_adapter_swap():
    # Start with Mock
    mock = MockAdapter()
    manager = ModelManager(mock)

    res1 = await manager.request(1, lambda: manager.adapter.chat([], content="hi"))
    # In MockAdapter, chat returns "Mock response to chat"
    # Wait, the lambda needs to call the adapter

    # Correction: The lambda should be the actual call
    res1 = await manager.request(1, lambda: mock.chat([], content="hi"))
    assert res1 == "Mock response to chat"

    # Swap adapter
    manager.adapter = OllamaAdapter()
    # This would fail if Ollama isn't running, so we use Mock for the swap verification
    manager.adapter = MockAdapter()
    res2 = await manager.request(1, lambda: manager.adapter.chat([], content="hi"))
    assert res2 == "Mock response to chat"

    await manager.shutdown()

@pytest.mark.asyncio
async def test_structured_output_mock():
    adapter = MockAdapter()
    res = await adapter.structured([], SimpleSchema)
    assert isinstance(res, SimpleSchema)
    assert res.answer == "mock_value"
