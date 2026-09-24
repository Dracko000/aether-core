"""Anthropic Messages API adapter (Claude)."""
import json
import logging
import re
from typing import Any, Dict, List

import httpx
from pydantic import BaseModel

from aether.model.adapter import ModelAdapter

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AnthropicAdapter(ModelAdapter):
    """Native Anthropic ``/v1/messages`` adapter.

    System prompts are mapped to the top-level ``system`` field (Anthropic
    rejects a ``system`` role inside ``messages``). Structured output uses
    instructions + strict schema parsing.
    """

    def __init__(
        self,
        base_url: str = "https://api.anthropic.com",
        api_key: str = "",
        model_name: str = "claude-sonnet-4-5",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    @staticmethod
    def _split_system(messages: List[Dict[str, str]]) -> tuple:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        return "\n".join(system_parts), rest

    async def _messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        system, body_messages = self._split_system(messages)
        body: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": kwargs.pop("max_tokens", 2048),
            "messages": body_messages or [{"role": "user", "content": ""}],
            **kwargs,
        }
        if system:
            body["system"] = system
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/messages",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        try:
            return "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
        except (KeyError, TypeError) as exc:
            raise RuntimeError(f"unexpected Anthropic response: {str(data)[:200]}") from exc

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        content = await self._messages(messages, **kwargs)
        if not content:
            raise RuntimeError("model returned an empty reply")
        return content

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

    async def structured(
        self,
        messages: List[Dict[str, str]],
        schema: type[BaseModel],
        **kwargs,
    ) -> BaseModel:
        schema_hint = json.dumps(schema.model_json_schema())
        guided = messages + [
            {
                "role": "user",
                "content": (
                    "Respond with a single JSON object matching this JSON schema "
                    f"and nothing else:\n{schema_hint}"
                ),
            }
        ]
        content = await self._messages(guided, **kwargs)
        text = content.strip()
        m = _JSON_FENCE_RE.search(text)
        if m:
            text = m.group(1).strip()
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
        return schema.model_validate_json(text)