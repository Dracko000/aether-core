"""Model provider registry — local + remote backends.

Mirrors the plugin structure of NousResearch/hermes-agent
(``plugins/model-providers/``): each provider is a small profile carrying
its display metadata, base URL, API-key env var, model catalogue URL and
sensible fallback models. Local Ollama is always available (no key);
remote providers are opt-in and need their API key.

The engine talks to every provider through a :class:`ModelAdapter`
(factory in ``aether.model.factory``), so switching providers never touches
the cognitive pipeline.
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderProfile:
    """Static metadata for one model backend (registry entry)."""

    id: str
    display_name: str
    description: str
    kind: str  # "ollama" | "openai" (OpenAI-compatible) | "anthropic"
    base_url: str
    api_key_env: str = ""          # env var holding the API key ("" = no key needed)
    models_url: str = ""           # catalogue endpoint for model listing
    signup_url: str = ""           # where a user gets an API key
    default_model: str = ""        # used when no explicit model is configured
    fallback_models: tuple = field(default_factory=tuple)


PROVIDERS: Dict[str, ProviderProfile] = {}


def register_provider(profile: ProviderProfile) -> ProviderProfile:
    """Register a provider profile (idempotent by id)."""
    PROVIDERS[profile.id] = profile
    return profile


def get_provider(provider_id: str) -> Optional[ProviderProfile]:
    return PROVIDERS.get((provider_id or "").lower().strip())


def provider_options() -> List[dict]:
    """Public metadata for the setup console / API (never includes keys)."""
    out = []
    for profile in PROVIDERS.values():
        out.append(
            {
                "id": profile.id,
                "display_name": profile.display_name,
                "description": profile.description,
                "kind": profile.kind,
                "needs_key": bool(profile.api_key_env),
                "key_configured": bool(os.environ.get(profile.api_key_env)),
                "base_url": profile.base_url,
                "signup_url": profile.signup_url,
                "default_model": profile.default_model,
            }
        )
    return sorted(out, key=lambda p: (p["kind"] != "ollama", p["id"]))


async def fetch_provider_models(
    provider_id: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 8.0,
) -> List[str]:
    """List model ids from a provider's catalogue (None-ish on failure).

    ``api_key``/``base_url`` override the profile defaults (used by the
    setup form before anything is saved).
    """
    profile = get_provider(provider_id)
    if profile is None:
        return []
    base = (base_url or profile.base_url).rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if profile.kind == "ollama":
                resp = await client.get(f"{base}/api/tags")
                resp.raise_for_status()
                return [m.get("name") for m in resp.json().get("models", [])]

            key = api_key or os.environ.get(profile.api_key_env, "")
            headers = {}
            url = profile.models_url or f"{base}/models"
            if profile.kind == "anthropic":
                headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
            elif key:
                headers = {"Authorization": f"Bearer {key}"}

            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if profile.kind == "anthropic":
                return [m.get("id") for m in data.get("data", [])]
            return [m.get("id") for m in data.get("data", [])]
    except Exception as exc:  # catalogues are best-effort
        logger.debug("fetch_provider_models(%s): %s", provider_id, exc)
        return []


# ------------------------------------------------------------------ profiles

register_provider(
    ProviderProfile(
        id="ollama",
        display_name="Ollama (local)",
        description="Local models on this machine — no API key, fully private.",
        kind="ollama",
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        default_model="llama3.2:1b",
    )
)

register_provider(
    ProviderProfile(
        id="openai",
        display_name="OpenAI",
        description="GPT models via api.openai.com.",
        kind="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        models_url="https://api.openai.com/v1/models",
        signup_url="https://platform.openai.com/api-keys",
        default_model="gpt-4o-mini",
        fallback_models=("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"),
    )
)

register_provider(
    ProviderProfile(
        id="openrouter",
        display_name="OpenRouter",
        description="Unified API for 300+ models (OpenAI, Anthropic, Google, …).",
        kind="openai",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models_url="https://openrouter.ai/api/v1/models",
        signup_url="https://openrouter.ai/keys",
        default_model="anthropic/claude-3.5-sonnet",
        fallback_models=(
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o-mini",
            "google/gemini-2.0-flash",
            "meta-llama/llama-3.1-8b-instruct",
        ),
    )
)

register_provider(
    ProviderProfile(
        id="groq",
        display_name="Groq",
        description="Ultra-fast LPU inference (Llama, Mixtral, …).",
        kind="openai",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        models_url="https://api.groq.com/openai/v1/models",
        signup_url="https://console.groq.com/keys",
        default_model="llama-3.3-70b-versatile",
        fallback_models=("llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
    )
)

register_provider(
    ProviderProfile(
        id="deepseek",
        display_name="DeepSeek",
        description="DeepSeek chat & reasoner models (OpenAI-compatible API).",
        kind="openai",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        models_url="https://api.deepseek.com/v1/models",
        signup_url="https://platform.deepseek.com/api_keys",
        default_model="deepseek-chat",
        fallback_models=("deepseek-chat", "deepseek-reasoner"),
    )
)

register_provider(
    ProviderProfile(
        id="xai",
        display_name="xAI (Grok)",
        description="Grok models via the xAI API.",
        kind="openai",
        base_url="https://api.x.ai/v1",
        api_key_env="XAI_API_KEY",
        models_url="https://api.x.ai/v1/models",
        signup_url="https://console.x.ai/",
        default_model="grok-2-latest",
        fallback_models=("grok-2-latest", "grok-3-mini"),
    )
)

register_provider(
    ProviderProfile(
        id="gemini",
        display_name="Google Gemini",
        description="Gemini models via the OpenAI-compatible Google endpoint.",
        kind="openai",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key_env="GEMINI_API_KEY",
        models_url="https://generativelanguage.googleapis.com/v1beta/openai/models",
        signup_url="https://aistudio.google.com/apikey",
        default_model="gemini-2.0-flash",
        fallback_models=("gemini-2.0-flash", "gemini-2.5-flash"),
    )
)

register_provider(
    ProviderProfile(
        id="anthropic",
        display_name="Anthropic (Claude)",
        description="Claude models via the native Anthropic Messages API.",
        kind="anthropic",
        base_url="https://api.anthropic.com",
        api_key_env="ANTHROPIC_API_KEY",
        models_url="https://api.anthropic.com/v1/models",
        signup_url="https://console.anthropic.com/",
        default_model="claude-sonnet-4-5",
        fallback_models=("claude-sonnet-4-5", "claude-haiku-4-5"),
    )
)

ALL_PROVIDERS: List[str] = list(PROVIDERS.keys())