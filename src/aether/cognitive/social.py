from typing import List, Dict, Any, Optional
import re
import logging
from aether.storage.repositories_relationships import RelationshipRepository
from aether.memory.beliefs import BeliefManager
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("aether.cognitive.social")

# Words that carry no topical meaning for belief-content matching.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "being",
    "of", "in", "on", "to", "for", "with", "at", "by", "it", "its",
    "that", "this", "these", "those", "and", "or", "but", "not",
}

def _significant_tokens(text: str) -> set:
    """Content words (stopwords removed) in lowercase."""
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in _STOPWORDS}

def _beliefs_match(belief_content: str, fragment_content: str) -> bool:
    """True when two claims talk about the same subject.

    Uses direct substring containment first, then falls back to a significant
    keyword-overlap check so that paraphrases/contradictions like
    "The sky is blue" vs "The sky is not blue, it is green" are recognized.
    """
    a, b = belief_content.lower(), fragment_content.lower()
    if a in b or b in a:
        return True
    shared = _significant_tokens(a) & _significant_tokens(b)
    return len(shared) >= 2

class SocialResolver:
    """
    Manages the social dimensions of knowledge integration.
    Implements trust-weighting and contradiction resolution between agents.
    """
    def __init__(self, session: AsyncSession, belief_manager: BeliefManager):
        self.session = session
        self.belief_manager = belief_manager
        self.rel_repo = RelationshipRepository(session)

    async def resolve_knowledge_transfer(self, receiver_id: str, sender_id: str, fragment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates knowledge shared by another agent and determines the integration strategy
        for the receiver's belief system.
        """
        # 1. Get trust score
        rel = await self.rel_repo.get_relationship(receiver_id, sender_id)
        trust_score = rel.trust_score if rel else 0.5
        logger.info(f"Resolving knowledge from {sender_id} for {receiver_id} (Trust: {trust_score})")

        # 2. Extract the claim
        content = fragment.get("content")
        confidence = fragment.get("confidence", 0.5)

        if not content:
            return None

        # 3. Check for existing belief
        beliefs = await self.belief_manager.get_strongest_beliefs(receiver_id, min_confidence=0.1)
        existing_belief = next(
            (b for b in beliefs if _beliefs_match(b["content"], content)),
            None
        )

        if not existing_belief:
            # New information: integrate based on trust
            integrated_confidence = max(0.0, min(1.0, confidence * trust_score))
            return {
                "action": "CREATE",
                "content": content,
                "confidence": integrated_confidence,
                "reason": "New information from trusted source"
            }
        else:
            # Potential contradiction or reinforcement
            # Trigger contradiction if keywords like 'not', 'false', 'wrong' are present
            # OR if the content is markedly different but talking about the same thing
            is_contradiction = any(word in content.lower() for word in ["not", "false", "wrong", "incorrect"])

            if is_contradiction:
                # Resolution: Trust + Evidence Strength
                if trust_score > existing_belief["confidence"]:
                    return {
                        "action": "OVERRIDE",
                        "content": content,
                        "confidence": trust_score,
                        "reason": "Overridden by higher trust source"
                    }
                else:
                    return {
                        "action": "IGNORE",
                        "reason": "Existing belief is stronger than source trust"
                    }
            else:
                # Reinforcement
                integrated_confidence = max(0.0, min(1.0, existing_belief["confidence"] + (0.1 * trust_score)))
                return {
                    "action": "REINFORCE",
                    "belief_id": existing_belief["belief_id"],
                    "confidence": integrated_confidence,
                    "reason": "Reinforced by trusted source"
                }
