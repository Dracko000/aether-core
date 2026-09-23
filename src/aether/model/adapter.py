from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ModelAdapter(ABC):
    """
    Abstract Base Class for LLM adapters.
    Standardizes the interface for all model backends to ensure
    backend modularity and replaceability.
    """

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Interactive chat completion.
        :param messages: List of messages with 'role' and 'content'.
        :return: The model's response string.
        """
        pass

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Single prompt completion.
        :param prompt: The input text.
        :return: The model's generated completion.
        """
        pass

    @abstractmethod
    async def structured(self, messages: List[Dict[str, str]], schema: type[BaseModel], **kwargs) -> BaseModel:
        """
        Structured output generation using Grammar-first constraints.
        :param messages: List of messages with 'role' and 'content'.
        :param schema: The Pydantic model the output must match.
        :return: An instance of the provided Pydantic schema.
        """
        pass
