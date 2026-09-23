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
    """Verify the ModelManager can dynamically swap model adapters."""
    # Initialize with MockAdapter
    mock = MockAdapter()
    manager = ModelManager(mock)

    # Execute request using initial adapter
    res1 = await manager.request(1, lambda: mock.chat([], content="hi"))
    assert res1 == "Mock response to chat"

    # Swap to a different adapter implementation
    manager.adapter = MockAdapter()
    res2 = await manager.request(1, lambda: manager.adapter.chat([], content="hi"))
    assert res2 == "Mock response to chat"

    await manager.shutdown()

@pytest.mark.asyncio
async def test_structured_output_mock():
    """Verify the adapter produces correctly typed structured outputs."""
    adapter = MockAdapter()
    res = await adapter.structured([], SimpleSchema)
    assert isinstance(res, SimpleSchema)
    assert res.answer == "mock_value"
