from typing import List, Optional
import numpy as np

class EmbeddingModel:
    """
    Wrapper for generating embeddings.
    For the MVP, this implements a deterministic mock embedding model.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, text: str) -> np.ndarray:
        # Deterministic mock embedding based on text hash
        # In production, this would call a local model like sentence-transformers
        state = np.random.RandomState(sum(ord(c) for c in text))
        return state.randn(self.dimension).astype(np.float32)
