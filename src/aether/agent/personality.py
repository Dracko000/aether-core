from typing import Dict

class PersonalityManager:
    """
    Logic for mapping personality traits to prompt modifiers.
    """
    TRAIT_MODIFIERS = {
        "analytical": "Be concise, use bullet points, and prioritize logical reasoning.",
        "curious": "Ask clarifying questions and explore alternative possibilities.",
        "concise": "Provide the shortest possible correct answer."
    }

    @classmethod
    def get_modifier(cls, trait: str) -> str:
        return cls.TRAIT_MODIFIERS.get(trait, "")
