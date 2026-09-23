from typing import Dict, Any, List, Optional, Callable, Awaitable
from pydantic import BaseModel, Field

class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] # JSON Schema
    risk_level: str # "LOW", "MEDIUM", "HIGH"

class ToolRegistry:
    """
    Central registry for all available tools.
    """
    def __init__(self):
        self._tools: Dict[str, ToolSchema] = {}
        self._executors: Dict[str, Callable] = {}

    def register(self, schema: ToolSchema, executor: Callable):
        self._tools[schema.name] = schema
        self._executors[schema.name] = executor

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        return self._tools.get(name)

    def get_executor(self, name: str) -> Optional[Callable]:
        return self._executors.get(name)

    def list_tools(self) -> List[ToolSchema]:
        return list(self._tools.values())

# Global registry instance
registry = ToolRegistry()
