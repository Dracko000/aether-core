import pytest
from aether.model.mock import MockAdapter
from pydantic import BaseModel

class AgentSchema(BaseModel):
    result: str

@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = MockAdapter()
    assert await adapter.chat([]) == "Mock response to chat"
    assert await adapter.generate("hello") == "Mock response to generate"
    res = await adapter.structured([], AgentSchema)
    assert res.result == "mock_value"
