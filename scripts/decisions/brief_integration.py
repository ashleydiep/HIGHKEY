import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from .db import rest
from .expire_pending import expire_pending
from .log_decision import log_decision, LogDecisionInput
from .check_rec_history import check_rec_history
from .short_id import generate_unique_short_id

UTC = timezone.utc
DEBUG_LOG = Path(__file__).parent.parent.parent / "outputs" / "briefs" / "debug-log.jsonl"


@dataclass
class PendingRec:
    short_id: str
    id: str
    question: str
    created_at: str


@dataclass
class ReviewRow:
    id: str
    short_id: Optional[str]
    question: str
    chosen: Optional[str]
    outcome_assessed_at: str


@dataclass
class RevisitRow:
    id: str
    short_id: Optional[str]
    question: str
    chosen: Optional[str]
    re_surface_at: str


@dataclass
class PreBriefState:
    expired_now: int
    pending_count: int
    gate_active: bool
    pending_recs: list[PendingRec]
    reviews_due: list[ReviewRow]
    revisits_due: list[RevisitRow]


def run_pre_brief() -> PreBriefState:
    expired = expire_pending()

    pending_rows = rest(
        "GET",
        "decisions?source=eq.ai-recommendation&status=eq.pending&select=id,short_id,question,created_at&order=created_at.asc",
    ).json()
    pending_recs = [
        PendingRec(short_id=r["short_id"], id=r["id"], question=r["question"], created_at=r["created_at"])
        for r in pending_rows if r.get("short_id")
    ]

    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    review_rows = rest(
        "GET",
        f"decisions?outcome_assessed_at=lte.{now_iso}&actual_outcome=is.null&status=in.(logged,accepted)&select=id,short_id,question,chosen,outcome_assessed_at&order=outcome_assessed_at.asc&limit=5",
    ).json()
    reviews_due = [
        ReviewRow(id=r["id"], short_id=r.get("short_id"), question=r["question"],
                  chosen=r.get("chosen"), outcome_assessed_at=r["outcome_assessed_at"])
        for r in review_rows
    ]

    revisit_rows = rest(
        "GET",
        f"decisions?source=eq.ai-recommendation&status=eq.rejected&reason_category=eq.later&re_surface_at=lte.{now_iso}&select=id,short_id,question,chosen,re_surface_at&order=re_surface_at.asc&limit=5",
    ).json()
    revisits_due = [
        RevisitRow(id=r["id"], short_id=r.get("short_id"), question=r["question"],
                   chosen=r.get("chosen"), re_surface_at=r["re_surface_at"])
        for r in revisit_rows
    ]

    pending_count = len(pending_recs)
    return PreBriefState(
        expired_now=expired.expired,
        pending_count=pending_count,
        gate_active=pending_count >= 3,
        pending_recs=pending_recs,
        reviews_due=reviews_due,
        revisits_due=revisits_due,
    )


def build_section7_prompt_fragment(state: PreBriefState) -> str:
    if state.gate_active:
        return ""
    return """

## Section 7: Today's Recommendations

Based on Ashley's current metrics, pipeline, and goals, generate 0–3 specific, actionable recommendations for today. Be selective — only emit a rec if it's genuinely valuable.

Format each recommendation EXACTLY as:
[REC] **<recommendation>** <1-sentence rationale>

If no strong recommendations: [REC] (none)

Rules:
- Max 3 recs
- Each must be specific and actionable for today
- Bold only the recommendation text, not the rationale
- One line per rec"""


def post_process_brief(brief: str, module: str = "daily") -> dict:
    lines = brief.split("\n")
    output_lines = []
    emitted = []
    suppressed = []

    for line in lines:
        if not line.strip().startswith("[REC]"):
            output_lines.append(line)
            continue

        content = line.strip()[5:].strip()  # strip "[REC]"

        if content == "(none)":
            continue  # strip silently

        # Parse **rec text** rationale
        m = re.match(r"\*\*(.+?)\*\*\s*(.*)", content)
        if not m:
            output_lines.append(line)
            continue

        rec_text = m.group(1).strip()
        rationale = m.group(2).strip()
        issue_sig = rec_text.lower()[:80]

        history = check_rec_history(rec_text)

        if history.action == "suppress":
            suppressed.append({"rec": rec_text, "reason": history.reason})
            try:
                DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
                with open(DEBUG_LOG, "a") as f:
                    f.write(json.dumps({"suppressed": rec_text, "reason": history.reason}) + "\n")
            except Exception:
                pass
            continue

        result = log_decision(LogDecisionInput(
            question=rec_text,
            rationale=rationale,
            source="ai-recommendation",
            status="pending",
            module=module,
            issue_signature=issue_sig,
        ))
        short_id = result.short_id

        if history.action == "boost" and history.historical_accept_rate:
            rate_pct = int(history.historical_accept_rate * 100)
            prefix = f"[{short_id}, boosted: {rate_pct}% on {history.similar_count} similar past]"
        else:
            prefix = f"[{short_id}]"

        output_lines.append(f"{prefix} **{rec_text}** {rationale}")
        emitted.append({"short_id": short_id, "rec": rec_text})

    return {"brief": "\n".join(output_lines), "emitted": emitted, "suppressed": suppressed}


def render_section7_gated(state: PreBriefState) -> str:
    rec_list = "\n".join(
        f"  - {r.short_id} (pending since {r.created_at[:10]})"
        for r in state.pending_recs
    )
    return f"\n## 7. Today's Recommendations\n\n⏸ {state.pending_count} recommendation(s) waiting for your response before new ones are issued:\n\n{rec_list}\n\nReply `accept <id>` or `reject <id> <category>` in Telegram to clear the queue."


def render_reviews_due_block(state: PreBriefState) -> str:
    if not state.reviews_due:
        return ""
    rows = "\n".join(
        f"  - {r.question[:60]} (due {r.outcome_assessed_at[:10]})"
        for r in state.reviews_due
    )
    return f"\n### Decisions Due for Review\n\n{rows}\n\nRun `/decide review` to log outcomes."


def render_revisit_block(state: PreBriefState) -> str:
    if not state.revisits_due:
        return ""
    rows = "\n".join(
        f"  - [{r.short_id}] {r.question[:60]}"
        for r in state.revisits_due
    )
    return f"\n### Revisit (Deferred)\n\nThese recs were deferred and are ready for reconsideration:\n\n{rows}"


def mark_revisits_surfaced(state: PreBriefState) -> None:
    for r in state.revisits_due:
        try:
            rest("PATCH", f"decisions?id=eq.{r.id}", json={"re_surface_at": None})
        except Exception:
            pass


def render_section8(brief_date: datetime) -> str:
    if brief_date.weekday() != 0:  # 0 = Monday
        return ""

    from_date = (brief_date.replace(tzinfo=UTC) - __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows = rest(
        "GET",
        f"decisions?created_at=gte.{from_date}&select=id,short_id,source,status,reason_category,question,company,tags&order=created_at.desc",
    ).json()

    total = len(rows)
    ai_recs = [r for r in rows if r["source"] == "ai-recommendation"]
    accepted = sum(1 for r in ai_recs if r["status"] == "accepted")
    rejected = sum(1 for r in ai_recs if r["status"] == "rejected")
    expired = sum(1 for r in ai_recs if r["status"] == "expired")
    manual = sum(1 for r in rows if r["source"] == "manual")
    graded = accepted + rejected
    accept_rate = f"{int(accepted/graded*100)}%" if graded else "n/a"

    deferred = rest(
        "GET",
        "decisions?source=eq.ai-recommendation&status=eq.rejected&reason_category=eq.later&re_surface_at=not.is.null&select=short_id,question",
    ).json()

    section = f"""
## 8. Weekly Decision Summary

**Activity (last 7 days):** {total} decisions logged — {len(ai_recs)} AI recs, {manual} manual
**True acceptance rate:** {accept_rate} ({accepted} accepted / {rejected} rejected / {expired} expired)
"""

    if deferred:
        items = "\n".join(f"  - [{r['short_id']}] {r['question'][:60]}" for r in deferred[:5])
        section += f"\n**Deferred queue ({len(deferred)}):**\n{items}\n"

    section += "\n**Autonomy Ladder:** Inform → *Recommend* → Confirm → Autonomous\nKeep accepting quality recs to advance to Confirm mode."

    return section


def build_evening_recap() -> str:
    today = datetime.now(UTC).date().isoformat()
    rows = rest(
        "GET",
        f"decisions?source=eq.ai-recommendation&status=eq.pending&created_at=gte.{today}T00:00:00Z&select=short_id,question&order=created_at.asc",
    ).json()

    if not rows:
        return "No open recs from this morning. Clean slate. ✓"

    items = "\n".join(f"  [{r['short_id']}] {r['question']}" for r in rows)
    return f"""## Evening Recap — Pending Recommendations

{len(rows)} rec(s) from this morning still open:

{items}

Reply in Telegram:
  `accept {rows[0]['short_id']}` — accept
  `reject {rows[0]['short_id']} disagree` — not right
  `reject {rows[0]['short_id']} later 3` — remind in 3 days
"""
