from enum import Enum, auto
from typing import List

class AgentState(Enum):
    CREATED = auto()
    INITIALIZED = auto()
    IDLE = auto()
    AWAKENED = auto()
    PERCEIVING = auto()
    THINKING = auto()
    PLANNING = auto()
    ACTING = auto()
    OBSERVING = auto()
    VERIFYING = auto()
    REFLECTING = auto()
    LEARNING = auto()
    SAVING = auto()
    SLEEPING = auto()

class LifecycleManager:
    # Define valid transitions
    TRANSITIONS = {
        AgentState.CREATED: [AgentState.INITIALIZED],
        AgentState.INITIALIZED: [AgentState.IDLE],
        AgentState.IDLE: [AgentState.AWAKENED, AgentState.SLEEPING],
        AgentState.AWAKENED: [AgentState.PERCEIVING, AgentState.THINKING, AgentState.IDLE],
        AgentState.PERCEIVING: [AgentState.THINKING, AgentState.IDLE],
        AgentState.THINKING: [AgentState.PLANNING, AgentState.ACTING, AgentState.OBSERVING, AgentState.IDLE],
        AgentState.PLANNING: [AgentState.ACTING, AgentState.IDLE],
        AgentState.ACTING: [AgentState.OBSERVING, AgentState.IDLE],
        AgentState.OBSERVING: [AgentState.VERIFYING, AgentState.THINKING, AgentState.IDLE],
        AgentState.VERIFYING: [AgentState.REFLECTING, AgentState.THINKING, AgentState.IDLE],
        AgentState.REFLECTING: [AgentState.LEARNING, AgentState.IDLE],
        AgentState.LEARNING: [AgentState.SAVING, AgentState.IDLE],
        AgentState.SAVING: [AgentState.IDLE, AgentState.SLEEPING],
        AgentState.SLEEPING: [AgentState.AWAKENED, AgentState.IDLE],
    }

    @classmethod
    def validate_transition(cls, current: AgentState, next_state: AgentState) -> bool:
        return next_state in cls.TRANSITIONS.get(current, [])
