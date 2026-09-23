from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

@dataclass
class AgentEvent:
    """
    System event that triggers agent activation or state transitions.
    """
    event_type: str
    agent_id: str
    payload: Dict[str, Any]
    priority: int = 10 # Lower values indicate higher priority
    source: str = "system"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    scheduled_at: Optional[float] = None
