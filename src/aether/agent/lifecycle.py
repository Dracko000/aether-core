from enum import Enum, auto
from typing import List

class AgentState(Enum):
    CREATED = auto()
    INITIALIZED = auto()
    IDLE = auto()
    AWAKENED = auto()
    THINKING = auto()
    ACTING = auto()
    OBSERVING = auto()
    REFLECTING = auto()
    LEARNING = auto()
    SLEEPING = auto()

class LifecycleManager:
    # Define valid transitions
    TRANSITIONS = {
        AgentState.CREATED: [AgentState.INITIALIZED],
        AgentState.INITIALIZED: [AgentState.IDLE],
        AgentState.IDLE: [AgentState.AWAKENED, AgentState.SLEEPING],
        AgentState.AWAKENED: [AgentState.THINKING, AgentState.IDLE],
        AgentState.THINKING: [AgentState.ACTING, AgentState.OBSERVING, AgentState.IDLE],
        AgentState.ACTING: [AgentState.OBSERVING, AgentState.IDLE],
        AgentState.OBSERVING: [AgentState.THINKING, AgentState.REFLECTING, AgentState.IDLE],
        AgentState.REFLECTING: [AgentState.LEARNING, AgentState.IDLE],
        AgentState.LEARNING: [AgentState.IDLE],
        AgentState.SLEEPING: [AgentState.AWAKENED, AgentState.IDLE],
    }

    @classmethod
    def validate_transition(cls, current: AgentState, next_state: AgentState) -> bool:
        return next_state in cls.TRANSITIONS.get(current, [])
