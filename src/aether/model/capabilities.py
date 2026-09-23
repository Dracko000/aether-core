from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any

@dataclass
class ModelCapabilities:
    """
    Defines the technical and cognitive capabilities of a specific model version.
    """
    model_id: str
    max_context: int
    supports_gnbf: bool = True
    supports_tool_use: bool = True
    reasoning_level: int = 1 # 1: Basic, 2: Advanced, 3: Expert
    supported_formats: Set[str] = field(default_factory=lambda: {"json", "markdown"})
    latency_tier: str = "medium" # low, medium, high

class CapabilityMatrix:
    """
    Registry of available models and their capabilities.
    """
    def __init__(self):
        self._matrix: Dict[str, ModelCapabilities] = {}

    def register_model(self, capabilities: ModelCapabilities):
        self._matrix[capabilities.model_id] = capabilities

    def get_capabilities(self, model_id: str) -> Optional[ModelCapabilities]:
        return self._matrix.get(model_id)

    def find_best_model(self, required_capabilities: Dict[str, Any]) -> Optional[str]:
        """
        Find the most capable model that meets the minimum requirements.
        """
        best_model = None
        highest_reasoning = -1

        for model_id, caps in self._matrix.items():
            meets_reqs = True
            for req_attr, req_val in required_capabilities.items():
                if getattr(caps, req_attr, None) != req_val:
                    # For context, we check if it's at least the required size
                    if req_attr == "max_context" and caps.max_context >= req_val:
                        continue
                    meets_reqs = False
                    break
            
            if meets_reqs and caps.reasoning_level > highest_reasoning:
                highest_reasoning = caps.reasoning_level
                best_model = model_id
        
        return best_model
