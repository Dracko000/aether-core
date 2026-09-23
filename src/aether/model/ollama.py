import httpx
import json
from aether.model.adapter import ModelAdapter
from aether.model.grammar import pydantic_to_gbnf
from pydantic import BaseModel
from typing import List, Dict, Any

class OllamaAdapter(ModelAdapter):
    """
    Adapter for the Ollama backend.
    Uses the /api/generate and /api/chat endpoints.
    """
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3"):
        self.base_url = base_url
        self.model_name = model_name

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    **kwargs
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")

    async def generate(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json().get("response", "")

    async def structured(self, messages: List[Dict[str, str]], schema: type[BaseModel], **kwargs) -> BaseModel:
        grammar = pydantic_to_gbnf(schema)

        # Consolidate messages into a single prompt for /api/generate
        # to ensure broader compatibility with grammar support in Ollama.
        prompt = ""
        for msg in messages:
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "assistant: "

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "grammar": grammar
                    },
                    **kwargs
                },
                timeout=60.0
            )
            response.raise_for_status()
            content = response.json().get("response", "")
            return schema.model_validate_json(content)
