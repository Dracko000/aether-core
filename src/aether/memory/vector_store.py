from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np
import os
import pickle

class VectorStore(ABC):
    @abstractmethod
    async def add(self, vector: np.ndarray, metadata: dict, id: str):
        pass

    @abstractmethod
    async def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[float, dict]]:
        pass

    @abstractmethod
    async def delete(self, id: str):
        pass

class LocalVectorStore(VectorStore):
    """
    A lightweight local vector store using NumPy for cosine similarity.
    Persists indices and vectors to disk using pickle for the MVP.
    """
    def __init__(self, storage_path: str = "./data/vectors/store.pkl"):
        self.storage_path = storage_path
        self.vectors = np.array([], dtype=np.float32).reshape(0, 0)
        self.metadata = []
        self.ids = []
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "rb") as f:
                data = pickle.load(f)
                self.vectors = data["vectors"]
                self.metadata = data["metadata"]
                self.ids = data["ids"]

    def _save(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "wb") as f:
            pickle.dump({
                "vectors": self.vectors,
                "metadata": self.metadata,
                "ids": self.ids
            }, f)

    async def add(self, vector: np.ndarray, metadata: dict, id: str):
        vector = vector.astype(np.float32)
        if self.vectors.size == 0:
            self.vectors = vector.reshape(1, -1)
        else:
            self.vectors = np.vstack([self.vectors, vector])

        self.metadata.append(metadata)
        self.ids.append(id)
        self._save()

    async def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[float, dict]]:
        if self.vectors.size == 0:
            return []

        query_vector = query_vector.astype(np.float32).reshape(1, -1)

        # Cosine Similarity: (A . B) / (||A|| ||B||)
        norm_v = np.linalg.norm(self.vectors, axis=1)
        norm_q = np.linalg.norm(query_vector)

        similarities = np.dot(self.vectors, query_vector.T).flatten() / (norm_v * norm_q)

        # Get top K indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(float(similarities[i]), self.metadata[i]) for i in top_indices]

    async def delete(self, id: str):
        if id in self.ids:
            idx = self.ids.index(id)
            self.vectors = np.delete(self.vectors, idx, axis=0)
            self.metadata.pop(idx)
            self.ids.pop(idx)
            self._save()
