from aether.agent.lifecycle import AgentState, LifecycleManager

def test_valid_transitions():
    assert LifecycleManager.validate_transition(AgentState.CREATED, AgentState.INITIALIZED) is True
    assert LifecycleManager.validate_transition(AgentState.IDLE, AgentState.AWAKENED) is True

def test_invalid_transitions():
    assert LifecycleManager.validate_transition(AgentState.CREATED, AgentState.ACTING) is False
