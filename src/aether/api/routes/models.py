"""Model registry API — exposes the capability matrix (v0.5 model migration).

Lets operators inspect which models Aether knows about and ask the matrix
which registered model fits a given cognitive workload, e.g.:

    GET /models
    GET /models/select?reasoning_level=2&max_context=8192
"""

from fastapi import APIRouter, Query
from typing import Any, Dict, List

from aether.model.capabilities import CapabilityMatrix
from aether.model.factory import create_default_capability_matrix

router = APIRouter()

# Plain-data registry — safe to build at import time (no event loop / I/O).
_matrix: CapabilityMatrix = create_default_capability_matrix()


@router.get("")
async def list_models() -> List[Dict[str, Any]]:
    """Return every registered model and its capabilities."""
    models: List[Dict[str, Any]] = []
    for caps in _matrix.all_models():
        models.append(
            {
                "model_id": caps.model_id,
                "max_context": caps.max_context,
                "supports_gnbf": caps.supports_gnbf,
                "supports_tool_use": caps.supports_tool_use,
                "reasoning_level": caps.reasoning_level,
                "latency_tier": caps.latency_tier,
            }
        )
    return models


@router.get("/select")
async def select_model(
    reasoning_level: int = Query(1, ge=1, le=3, description="Minimum reasoning level (1 basic, 2 advanced, 3 expert)"),
    max_context: int = Query(4096, ge=1, description="Minimum context window, in tokens"),
) -> Dict[str, Any]:
    """Pick the most capable registered model meeting the requirements."""
    required = {"reasoning_level": reasoning_level, "max_context": max_context}
    from aether.model.factory import select_model_for

    model_id = select_model_for(required, matrix=_matrix)
    caps = _matrix.get_capabilities(model_id)
    return {
        "model_id": model_id,
        "reasoning_level": caps.reasoning_level if caps else None,
        "max_context": caps.max_context if caps else None,
        "requirements": required,
    }