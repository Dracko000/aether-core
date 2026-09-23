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
        # Instantiate the provided Pydantic schema with mock data
        mock_data = {}
        for field_name, field_info in schema.model_fields.items():
            field_type = field_info.annotation
            # Type-aware mock data generation
            if field_type == list or getattr(field_type, "__origin__", None) is list:
                mock_data[field_name] = ["mock_value"]
            elif field_type == dict or getattr(field_type, "__origin__", None) is dict:
                mock_data[field_name] = {"key": "mock_value"}
            elif field_type == int:
                mock_data[field_name] = 1
            elif field_info.metadata:
                # Provide a valid value for common Pydantic Field constraints
                mock_data[field_name] = "Positive" if "Positive" in str(field_info.metadata) else "mock_value"
            else:
                mock_data[field_name] = "mock_value"

        try:
            return schema(**mock_data)
        except Exception:
            # Fallback to basic model construction if strict validation fails
            return schema.model_construct(**mock_data)
