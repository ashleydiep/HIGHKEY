import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from .db import rest
from .embeddings import embed, prepare_decision_text
from .find_similar import find_similar_decisions, FindSimilarOptions, SimilarDecision
from .short_id import generate_unique_short_id

UTC = timezone.utc


@dataclass
class LogDecisionInput:
    question: str
    context: Optional[str] = None
    options: list = field(default_factory=list)
    chosen: Optional[str] = None
    rationale: Optional[str] = None
    expected_outcome: Optional[str] = None
    confidence_score: Optional[float] = None
    tags: list = field(default_factory=list)
    company: Optional[str] = None
    source: str = "manual"
    status: Optional[str] = None
    module: Optional[str] = None
    issue_signature: Optional[str] = None


@dataclass
class LogDecisionResult:
    id: str
    short_id: Optional[str]
    matches: list[SimilarDecision]


def log_decision(inp: LogDecisionInput) -> LogDecisionResult:
    # Find similar decisions (best-effort)
    try:
        matches = find_similar_decisions(inp.question, FindSimilarOptions(threshold=0.5, limit=5))
    except Exception:
        matches = []

    # Determine status
    if inp.status:
        status = inp.status
    elif inp.source == "ai-recommendation":
        status = "pending"
    else:
        status = "logged"

    # Generate short_id only for AI recs
    short_id = None
    if inp.source == "ai-recommendation":
        short_id = generate_unique_short_id()

    # Set outcome review date
    outcome_date = None
    if status in ("logged", "accepted"):
        outcome_date = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "question": inp.question,
        "source": inp.source,
        "status": status,
        "options": inp.options or [],
        "tags": inp.tags or [],
    }
    if inp.context:
        payload["context"] = inp.context
    if inp.chosen:
        payload["chosen"] = inp.chosen
    if inp.rationale:
        payload["rationale"] = inp.rationale
    if inp.expected_outcome:
        payload["expected_outcome"] = inp.expected_outcome
    if inp.confidence_score is not None:
        payload["confidence_score"] = inp.confidence_score
    if inp.company:
        payload["company"] = inp.company
    if inp.module:
        payload["module"] = inp.module
    if inp.issue_signature:
        payload["issue_signature"] = inp.issue_signature
    if short_id:
        payload["short_id"] = short_id
    if outcome_date:
        payload["outcome_assessed_at"] = outcome_date

    resp = rest("POST", "decisions", json=payload)
    row = resp.json()[0]

    # Async embed (non-fatal)
    def _embed_async():
        try:
            text = prepare_decision_text(inp.question, inp.chosen or "", inp.rationale or "")
            vec = embed(text)
            rest("PATCH", f"decisions?id=eq.{row['id']}", json={"embedding": vec})
        except Exception:
            pass

    threading.Thread(target=_embed_async, daemon=True).start()

    return LogDecisionResult(id=row["id"], short_id=row.get("short_id"), matches=matches)
