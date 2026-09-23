from typing import Dict

class PersonalityManager:
    """
    Manages the mapping of personality traits to linguistic and cognitive modifiers.
    """
    TRAIT_MODIFIERS = {
        "analytical": "Be concise, use bullet points, and prioritize logical reasoning.",
        "curious": "Ask clarifying questions and explore alternative possibilities.",
        "concise": "Provide the shortest possible correct answer."
    }

    @classmethod
    def get_modifier(cls, trait: str) -> str:
        """Retrieve the modifier associated with a specific personality trait."""
        return cls.TRAIT_MODIFIERS.get(trait, "")
