from dataclasses import dataclass, field
from typing import Optional
from .db import rpc
from .embeddings import embed, prepare_decision_text

DEFAULT_THRESHOLD = 0.5
DEFAULT_LIMIT = 10


@dataclass
class SimilarDecision:
    id: str
    short_id: Optional[str]
    question: str
    chosen: Optional[str]
    rationale: Optional[str]
    status: str
    source: str
    reason_category: Optional[str]
    actual_outcome: Optional[str]
    company: Optional[str]
    similarity: float
    created_at: str


@dataclass
class FindSimilarOptions:
    threshold: float = DEFAULT_THRESHOLD
    limit: int = DEFAULT_LIMIT
    company: Optional[str] = None
    sources: list = field(default_factory=list)
    statuses: list = field(default_factory=lambda: ["logged", "accepted"])


def find_similar_decisions(query_text: str, opts: Optional[FindSimilarOptions] = None) -> list[SimilarDecision]:
    if opts is None:
        opts = FindSimilarOptions()

    try:
        vec = embed(query_text, input_type="query")
    except Exception:
        return []

    try:
        rows = rpc("semantic_search", {
            "query_embedding": vec,
            "match_threshold": opts.threshold,
            "match_count": opts.limit * 4,
        })
    except Exception:
        return []

    results = []
    for r in rows:
        if opts.sources and r.get("source") not in opts.sources:
            continue
        if opts.statuses and r.get("status") not in opts.statuses:
            continue
        if opts.company and r.get("company") != opts.company:
            continue
        results.append(SimilarDecision(
            id=r["source_id"],
            short_id=r.get("short_id"),
            question=r["title"],
            chosen=None,
            rationale=None,
            status=r.get("status", ""),
            source=r.get("source", ""),
            reason_category=r.get("reason_category"),
            actual_outcome=r.get("actual_outcome"),
            company=r.get("company"),
            similarity=r["similarity"],
            created_at=r["created_at"],
        ))

    results.sort(key=lambda x: x.similarity, reverse=True)
    return results[:opts.limit]
