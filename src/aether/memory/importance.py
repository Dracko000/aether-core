from typing import Dict, Any

class ImportanceScorer:
    """
    Calculates a final importance score for a memory based on
    recurrence, goal alignment, and model-assigned weight.
    """
    @staticmethod
    def calculate(base_score: float, recurrence: int, goal_alignment: bool) -> float:
        score = base_score
        if recurrence > 1:
            score += 0.1 * (recurrence - 1)
        if goal_alignment:
            score += 0.2
        return min(1.0, score)
