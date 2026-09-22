import pytest
from aether.model.mock import MockAdapter
from pydantic import BaseModel

class TestSchema(BaseModel):
    result: str

@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = MockAdapter()
    assert await adapter.chat([]) == "Mock response to chat"
    assert await adapter.generate("hello") == "Mock response to generate"
    res = await adapter.structured([], TestSchema)
    assert res.result == "mock_value"
