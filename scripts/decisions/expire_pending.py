import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from .db import rest

UTC = timezone.utc
REC_EXPIRE_HOURS = int(os.environ.get("REC_EXPIRE_HOURS", "72"))


@dataclass
class ExpireResult:
    expired: int


def expire_pending() -> ExpireResult:
    cutoff = (datetime.now(UTC) - timedelta(hours=REC_EXPIRE_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = rest(
        "GET",
        f"decisions?source=eq.ai-recommendation&status=eq.pending&created_at=lt.{cutoff}&select=id",
    ).json()

    if not rows:
        return ExpireResult(expired=0)

    ids = [r["id"] for r in rows]
    # Patch each (Supabase REST doesn't support IN on PATCH easily without PostgREST v12)
    for rid in ids:
        rest("PATCH", f"decisions?id=eq.{rid}", json={"status": "expired"})

    return ExpireResult(expired=len(ids))
