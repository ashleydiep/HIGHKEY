#!/usr/bin/env python3
"""Weekly pattern rollup — run every Monday before the morning brief."""
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.decisions.db import rest

UTC = timezone.utc
DRY_RUN = "--dry-run" in sys.argv
SUCCESS_KEYWORDS = {"success", "right call", "worked", "positive", "yes"}


def main():
    rows = rest(
        "GET",
        "decisions?status=in.(logged,accepted)&select=id,company,tags,actual_outcome,chosen",
    ).json()

    # Filter out demo + untagged
    rows = [r for r in rows if r.get("tags") and "demo" not in (r.get("tags") or [])]

    # Group by company + first tag
    groups = {}
    for r in rows:
        tags = r.get("tags") or []
        if not tags:
            continue
        key = f"{r.get('company', 'general')}::{tags[0]}"
        groups.setdefault(key, []).append(r)

    patterns = []
    for key, group in groups.items():
        if len(group) < 3:
            continue
        company, tag = key.split("::", 1)
        outcomes = [r.get("actual_outcome") or "" for r in group]
        successes = sum(
            1 for o in outcomes
            if any(kw in o.lower() for kw in SUCCESS_KEYWORDS) and o.strip()
        )
        rated = sum(1 for o in outcomes if o.strip())
        success_rate = successes / rated if rated else None

        pattern = {
            "pattern_name": key,
            "description": f"{tag} decisions for {company}",
            "similar_decisions": [r["id"] for r in group],
            "total_decisions": len(group),
            "success_rate": success_rate,
            "last_used_at": datetime.now(UTC).isoformat(),
        }
        patterns.append(pattern)
        print(f"  {'[DRY] ' if DRY_RUN else ''}Pattern: {key} ({len(group)} decisions, {success_rate:.0%} success)" if success_rate else f"  Pattern: {key} ({len(group)} decisions)")

    if not DRY_RUN:
        import requests, os
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / ".env.local")
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        for p in patterns:
            requests.post(
                f"{url}/rest/v1/decision_patterns",
                headers={
                    "apikey": key, "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=representation",
                },
                json=p,
            ).raise_for_status()

    print(f"\n{'[DRY RUN] Would upsert' if DRY_RUN else 'Upserted'} {len(patterns)} pattern(s).")


if __name__ == "__main__":
    main()
