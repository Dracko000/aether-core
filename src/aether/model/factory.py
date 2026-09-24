"""Model wiring factory — turns configuration into a live model stack.

Production default is a local Ollama backend (no API key required), which
fits the constrained-memory design of :class:`ModelManager` and the
grammar-first structured output used by the cognitive pipeline.

``ModelManager`` spawns its worker task in ``__init__``, so it must be
constructed inside a *running* event loop (lifespan startup, a request
handler, or an async test) — never at module import time.
"""

from typing import Any, Dict, Optional

from aether.config import settings
from aether.model.adapter import ModelAdapter
from aether.model.capabilities import CapabilityMatrix, ModelCapabilities
from aether.model.manager import ModelManager
from aether.model.ollama import OllamaAdapter

# Default registry of Ollama models with conservative capability estimates.
#   reasoning_level: 1 = basic, 2 = advanced, 3 = expert
# The small tiers default because the ModelManager was designed for an ~8GB
# RAM footprint; the 70B tier is only meaningful on hosts that can run it.
DEFAULT_MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "llama3": {
        "max_context": 8192,
        "reasoning_level": 1,
        "latency_tier": "low",
    },
    "qwen2.5:7b": {
        "max_context": 32768,
        "reasoning_level": 1,
        "latency_tier": "medium",
    },
    "mistral": {
        "max_context": 8192,
        "reasoning_level": 2,
        "latency_tier": "medium",
    },
    "deepseek-r1:7b": {
        "max_context": 8192,
        "reasoning_level": 2,
        "latency_tier": "medium",
    },
    "llama3:70b": {
        "max_context": 8192,
        "reasoning_level": 3,
        "latency_tier": "high",
    },
}


def register_default_models(matrix: CapabilityMatrix) -> CapabilityMatrix:
    """Register the default Ollama model set into ``matrix`` (in place)."""
    for model_id, caps in DEFAULT_MODEL_REGISTRY.items():
        matrix.register_model(
            ModelCapabilities(
                model_id=model_id,
                max_context=caps["max_context"],
                supports_gnbf=True,
                supports_tool_use=True,
                reasoning_level=caps["reasoning_level"],
                latency_tier=caps["latency_tier"],
            )
        )
    return matrix


def create_default_capability_matrix() -> CapabilityMatrix:
    """Return a fresh capability matrix pre-loaded with the default models."""
    return register_default_models(CapabilityMatrix())


def build_adapter() -> ModelAdapter:
    """Build the production adapter from configuration (Ollama default)."""
    return OllamaAdapter(
        base_url=settings.OLLAMA_BASE_URL,
        model_name=settings.OLLAMA_MODEL,
    )


def build_model_manager() -> ModelManager:
    """Build the inference manager for the configured backend.

    Must be called inside a running event loop — see module docstring.
    """
    return ModelManager(build_adapter())


def select_model_for(
    required: Dict[str, Any],
    matrix: Optional[CapabilityMatrix] = None,
) -> str:
    """Pick the most capable registered model satisfying ``required``.

    Falls back to the configured default model (``OLLAMA_MODEL``) when no
    registered model meets the requirements but the default itself is
    registered — keeps a custom config working without raising.
    """
    matrix = matrix or create_default_capability_matrix()
    best = matrix.find_best_model(required)
    if best is not None:
        return best

    candidate = settings.OLLAMA_MODEL
    if matrix.get_capabilities(candidate) is not None:
        return candidate

    raise ValueError(
        f"Configured model {candidate!r} is not registered in the capability "
        "matrix and no registered model satisfies the required capabilities "
        f"{required!r}."
    )