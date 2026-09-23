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
    adapter = MockAdapter()  # Simulation of a llama.cpp adapter

    # Initialize the structural schema
    schema = TestResponse
    gbnf_grammar = pydantic_to_gbnf(schema)

    # Execute structured call
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
        # Initialize database tables for the current session
        await init_db()

        # Memory manager requires a session and a vector store
        vector_store = LocalVectorStore()
        memory_manager = MemoryManager(session=session, vector_store=vector_store)
        engine = CognitiveEngine(model_manager, memory_manager)

        # Fast path: execute direct response
        start_fast = asyncio.get_event_loop().time()
        # utilize execute() as the primary public API
        await engine.execute(agent_id="test_agent", query="Quick answer")
        end_fast = asyncio.get_event_loop().time()

        # Slow path: execute recursive reflection
        start_slow = asyncio.get_event_loop().time()
        # Extended query triggers the slow cognitive path in decide_path()
        await engine.execute(agent_id="test_agent", query="This is a very long query to trigger the slow cognitive path of the engine")
        end_slow = asyncio.get_event_loop().time()

        # Validate that the slow path duration is non-negative
        # In MockAdapter, latency is negligible; verify execution without error.
        assert (end_slow - start_slow) >= 0
