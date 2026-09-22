from aether.model.adapter import ModelAdapter
from pydantic import BaseModel
from typing import List, Dict, Any

class MockAdapter(ModelAdapter):
    """
    A deterministic mock implementation of ModelAdapter for testing
    the runtime without requiring a live LLM backend.
    """
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return "Mock response to chat"

    async def generate(self, prompt: str, **kwargs) -> str:
        return "Mock response to generate"

    async def structured(self, messages: List[Dict[str, str]], schema: type[BaseModel], **kwargs) -> BaseModel:
        # Create a mock instance of the provided Pydantic schema
        # Using schema.model_fields (Pydantic v2) to find fields
        mock_data = {field: "mock_value" for field in schema.model_fields}
        return schema(**mock_data)
