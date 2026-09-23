from typing import List, Dict, Any
from collections import deque

class WorkingMemory:
    """
    L1 Working Memory: Current task context.
    A volatile, sliding-window buffer of the most recent interactions.
    """
    def __init__(self, max_size: int = 20):
        self.buffer = deque(maxlen=max_size)

    def add(self, content: str, metadata: Dict[str, Any] = None):
        self.buffer.append({
            "content": content,
            "metadata": metadata or {}
        })

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()
