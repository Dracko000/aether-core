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
        mock_data = {}
        for field_name, field_info in schema.model_fields.items():
            field_type = field_info.annotation
            # Simple type-aware mock data
            if field_type == list or getattr(field_type, "__origin__", None) is list:
                mock_data[field_name] = ["mock_value"]
            elif field_type == dict or getattr(field_type, "__origin__", None) is dict:
                mock_data[field_name] = {"key": "mock_value"}
            elif field_type == int:
                mock_data[field_name] = 1
            elif field_info.metadata: # Handle Pydantic Field constraints like patterns
                # This is a simple mock; in a real scenario,
                # the LLM would be constrained by GBNF to match these patterns.
                # We just provide a generic valid value for common cases.
                mock_data[field_name] = "Positive" if "Positive" in str(field_info.metadata) else "mock_value"
            else:
                mock_data[field_name] = "mock_value"

        try:
            return schema(**mock_data)
        except Exception:
            # Fallback: if we can't mock it perfectly, just use a basic string
            # In a real test, we'd use more sophisticated mocking.
            return schema.model_construct(**mock_data)
