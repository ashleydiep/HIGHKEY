from dataclasses import dataclass, field
from typing import Optional
from .find_similar import find_similar_decisions, FindSimilarOptions

SIMILARITY_THRESHOLD = 0.65
MIN_SIMILAR_RECS = 3
SUPPRESS_DISAGREE_RATE = 0.6
BOOST_ACCEPT_RATE = 0.8


@dataclass
class RecHistoryResult:
    action: str  # "suppress" | "boost" | "emit_normal"
    reason: Optional[str] = None
    historical_accept_rate: Optional[float] = None
    similar_count: int = 0
    accept_count: int = 0
    disagree_count: int = 0
    similar_past: list = field(default_factory=list)


def check_rec_history(rec_text: str, company: Optional[str] = None) -> RecHistoryResult:
    opts = FindSimilarOptions(
        threshold=SIMILARITY_THRESHOLD,
        limit=20,
        company=company,
        sources=["ai-recommendation"],
        statuses=["accepted", "rejected"],
    )
    similar = find_similar_decisions(rec_text, opts)

    similar_past = [
        {
            "short_id": s.short_id,
            "question": s.question,
            "status": s.status,
            "reason_category": s.reason_category,
            "similarity": s.similarity,
        }
        for s in similar
    ]

    if len(similar) < MIN_SIMILAR_RECS:
        return RecHistoryResult(action="emit_normal", similar_count=len(similar), similar_past=similar_past)

    accepts = sum(1 for s in similar if s.status == "accepted")
    disagrees = sum(1 for s in similar if s.status == "rejected" and s.reason_category == "disagree")
    graded = accepts + disagrees

    if graded < 3:
        return RecHistoryResult(action="emit_normal", similar_count=len(similar),
                                accept_count=accepts, disagree_count=disagrees, similar_past=similar_past)

    if disagrees / graded > SUPPRESS_DISAGREE_RATE:
        return RecHistoryResult(
            action="suppress",
            reason=f"Suppressed: {disagrees}/{graded} similar past recs were disagreed with",
            similar_count=len(similar), accept_count=accepts, disagree_count=disagrees,
            similar_past=similar_past,
        )

    if accepts / graded > BOOST_ACCEPT_RATE:
        return RecHistoryResult(
            action="boost",
            reason=f"Boosted: {accepts}/{graded} similar past recs were accepted",
            historical_accept_rate=accepts / graded,
            similar_count=len(similar), accept_count=accepts, disagree_count=disagrees,
            similar_past=similar_past,
        )

    return RecHistoryResult(action="emit_normal", similar_count=len(similar),
                            accept_count=accepts, disagree_count=disagrees, similar_past=similar_past)
