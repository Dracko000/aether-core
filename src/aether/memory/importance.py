from typing import Dict, Any

class ImportanceScorer:
    """
    Computes the priority score of a memory based on recurrence,
    alignment with active goals, and model-assigned weights.
    """
    @staticmethod
    def calculate(base_score: float, recurrence: int, goal_alignment: bool) -> float:
        score = base_score
        if recurrence > 1:
            score += 0.1 * (recurrence - 1)
        if goal_alignment:
            score += 0.2
        return min(1.0, score)
