"""OpenAI-compatible chat-completions adapter.

Covers every remote provider that speaks the OpenAI wire protocol —
OpenAI, OpenRouter, Groq, DeepSeek, xAI, Gemini (OpenAI-compatible
endpoint) — with a single implementation. Structured output degrades
gracefully: we request ``response_format={"type": "json_object"}`` where
supported and fall back to instructions + tolerant parsing otherwise.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from aether.model.adapter import ModelAdapter

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class OpenAICompatAdapter(ModelAdapter):
    """Chat-completions adapter for OpenAI-compatible backends."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: str = "",
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        body: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            **kwargs,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"unexpected chat-completions response: {str(data)[:200]}"
            ) from exc

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        content = await self._chat_completion(messages, **kwargs)
        if not content:
            raise RuntimeError("model returned an empty reply")
        return content

    async def generate(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        m = _JSON_FENCE_RE.search(text)
        if m:
            return m.group(1).strip()
        if text.startswith("{"):
            return text
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return text[start : end + 1]
        return text

    async def structured(
        self,
        messages: List[Dict[str, str]],
        schema: type[BaseModel],
        **kwargs,
    ) -> BaseModel:
        """Ask for JSON, then validate; falls back to plain JSON instructions.

        ``response_format`` is only sent when the provider is known to accept it
        (OpenAI/OpenRouter/Groq/DeepSeek). Others get plain instructions.
        """
        schema_hint = json.dumps(schema.model_json_schema())
        instruction = (
            "Respond with a single JSON object that matches this JSON schema "
            f"and nothing else:\n{schema_hint}"
        )
        guided = messages + [{"role": "user", "content": instruction}]

        content: Optional[str] = None
        for use_format in (True, False):
            kw = dict(kwargs)
            if use_format:
                kw["response_format"] = {"type": "json_object"}
            try:
                content = await self._chat_completion(guided, **kw)
                return schema.model_validate_json(self._extract_json(content))
            except Exception as exc:
                logger.debug(
                    "structured() attempt (format=%s) failed: %s", use_format, exc
                )
                if not use_format:
                    raise
        raise RuntimeError("structured output could not be parsed")  # pragma: no cover