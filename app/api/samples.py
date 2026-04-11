# app/api/samples.py — Demo text samples for model testing via the imitate tab
#
# Returns pre-curated sentences with varied emotional subtext so that
# external tools (e.g. avocet imitate tab) can feed them to local LLMs
# and evaluate tone annotation quality without a live audio session.
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/samples", tags=["samples"])

# Each sample has a text field (the raw utterance) and a context field
# describing the situation — both fed into the imitate prompt template.
_SAMPLES: list[dict] = [
    {
        "text": "Sure, I can take care of that.",
        "context": "Employee responding to manager's request during a tense project meeting.",
        "category": "compliance",
    },
    {
        "text": "That's a really interesting approach.",
        "context": "Colleague reacting to a proposal they visibly disagree with.",
        "category": "polite_disagreement",
    },
    {
        "text": "I'll have it done by end of day.",
        "context": "Developer already working at capacity, second deadline added without discussion.",
        "category": "overcommitment",
    },
    {
        "text": "No, it's fine. Don't worry about it.",
        "context": "Person whose suggestion was dismissed without acknowledgment.",
        "category": "suppressed_hurt",
    },
    {
        "text": "I guess we could try it your way.",
        "context": "Team lead conceding after strong pushback, despite having a valid concern.",
        "category": "reluctant_agreement",
    },
    {
        "text": "That's one way to look at it.",
        "context": "Researcher responding to a peer who has misread their data.",
        "category": "implicit_correction",
    },
    {
        "text": "I appreciate you letting me know.",
        "context": "Employee informed their project is being cancelled with two hours notice.",
        "category": "formal_distress",
    },
    {
        "text": "We should probably circle back on this.",
        "context": "Manager avoiding a decision they don't want to make.",
        "category": "deferral",
    },
    {
        "text": "I just want to make sure I'm understanding correctly.",
        "context": "Autistic person who has been given contradictory instructions twice already.",
        "category": "clarification_exhaustion",
    },
    {
        "text": "Happy to help however I can!",
        "context": "Volunteer who has already put in 60 hours this month responding to another ask.",
        "category": "masking_burnout",
    },
]


@router.get("")
def list_samples(limit: int = 5) -> list[dict]:
    """Return a slice of demo annotation samples for model testing."""
    return _SAMPLES[:max(1, min(limit, len(_SAMPLES)))]
