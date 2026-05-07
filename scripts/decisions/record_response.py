from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from .db import rest

UTC = timezone.utc
VALID_CATEGORIES = {"disagree", "no-time", "redundant", "wrong-context", "later"}


@dataclass
class RecordResponseInput:
    rec_ids: list[str]
    action: str  # "accept" | "reject"
    category: Optional[str] = None
    note: Optional[str] = None
    surface_in_days: int = 7


@dataclass
class RecordResponseDetail:
    short_id: str
    id: str
    status: str
    reason_category: Optional[str]


@dataclass
class RecordResponseResult:
    updated: int
    not_found: list[str]
    details: list[RecordResponseDetail]


def record_recommendation_response(inp: RecordResponseInput) -> RecordResponseResult:
    if inp.action == "reject" and not inp.category:
        raise ValueError("category is required when action='reject'")
    if inp.category and inp.category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {VALID_CATEGORIES}")

    details = []
    not_found = []

    for short_id in inp.rec_ids:
        rows = rest(
            "GET",
            f"decisions?short_id=eq.{short_id}&source=eq.ai-recommendation&status=eq.pending&select=id,short_id,status,reason_category",
        ).json()

        if not rows:
            not_found.append(short_id)
            continue

        row = rows[0]

        if inp.action == "accept":
            outcome_date = (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            patch = {"status": "accepted", "outcome_assessed_at": outcome_date}
        else:
            patch = {"status": "rejected", "reason_category": inp.category}
            if inp.note:
                patch["rejection_note"] = inp.note
            if inp.category == "later":
                resurface = (datetime.now(UTC) + timedelta(days=inp.surface_in_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
                patch["re_surface_at"] = resurface

        rest("PATCH", f"decisions?id=eq.{row['id']}", json=patch)
        details.append(RecordResponseDetail(
            short_id=short_id,
            id=row["id"],
            status=inp.action + "ed",
            reason_category=inp.category,
        ))

    return RecordResponseResult(updated=len(details), not_found=not_found, details=details)
