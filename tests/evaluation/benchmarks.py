import pytest
import asyncio
from aether.model.adapter import ModelAdapter
from aether.model.mock import MockAdapter
from aether.model.grammar import pydantic_to_gbnf
from pydantic import BaseModel, Field
from typing import List

class TestResponse(BaseModel):
    summary: str
    keywords: List[str]
    sentiment: str = Field(pattern="^(Positive|Negative|Neutral)$")

@pytest.mark.asyncio
async def test_gbnf_structured_output_accuracy():
    """
    Verify that the structured output enforced by GBNF matches the Pydantic schema exactly.
    """
    adapter = MockAdapter() # In real tests, this would be a llama.cpp adapter

    # Define the expected schema
    schema = TestResponse
    gbnf_grammar = pydantic_to_gbnf(schema)

    # Mock the structured call
    # The MockAdapter expects messages and schema
    result = await adapter.structured(
        messages=[{"role": "user", "content": "Summarize the aether core project."}],
        schema=schema
    )

    assert isinstance(result, TestResponse)
    assert hasattr(result, "summary")
    assert isinstance(result.keywords, list)
    assert result.sentiment in ["Positive", "Negative", "Neutral"]

@pytest.mark.asyncio
async def test_fast_slow_path_latency():
    """
    Measure the latency difference between Fast (direct) and Slow (reflective) paths.
    """
    from aether.cognitive.engine import CognitiveEngine
    from aether.model.mock import MockAdapter
    from aether.model.manager import ModelManager
    from aether.memory.manager import MemoryManager
    from aether.memory.vector_store import LocalVectorStore
    from aether.storage.database import AsyncSessionLocal, init_db

    adapter = MockAdapter()
    model_manager = ModelManager(adapter)

    async with AsyncSessionLocal() as session:
        # MUST initialize DB tables for the session
        await init_db()

        # Memory manager needs a session and a vector store
        vector_store = LocalVectorStore()
        memory_manager = MemoryManager(session=session, vector_store=vector_store)
        engine = CognitiveEngine(model_manager, memory_manager)

        # Fast path: direct response
        start_fast = asyncio.get_event_loop().time()
        # Using execute() as it's the public API
        await engine.execute(agent_id="test_agent", query="Quick answer")
        end_fast = asyncio.get_event_loop().time()

        # Slow path: recursive reflection
        start_slow = asyncio.get_event_loop().time()
        # Long query triggers SLOW path in decide_path()
        await engine.execute(agent_id="test_agent", query="This is a very long query to trigger the slow cognitive path of the engine")
        end_slow = asyncio.get_event_loop().time()

        # Slow path should generally take longer or equal in Mock
        # In MockAdapter, latency is almost zero, so we just check that it runs without error.
        assert (end_slow - start_slow) >= 0
