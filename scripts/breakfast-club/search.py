#!/usr/bin/env python3
"""
Search Breakfast Club sessions by topic/question.
Used by the appointment booking agent to find Ashley's specific training.

Usage:
  python3 search.py "how to handle price objection"
  python3 search.py "seller motivation" --category sellers --limit 3
"""

import os
import sys
import json
import argparse
import requests
import voyageai

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
SUPABASE_URL   = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY   = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

VALID_CATEGORIES = [
    "sellers", "buyers", "objection_handlers", "tonality",
    "mindset", "scripts", "concepts", "closing", "follow_up", "roleplay"
]


def embed_query(query: str) -> list:
    client = voyageai.Client(api_key=VOYAGE_API_KEY)
    result = client.embed([query], model="voyage-3-large", input_type="query")
    return result.embeddings[0]


def search(query: str, category: str = None, limit: int = 5) -> list:
    embedding = embed_query(query)

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # Vector similarity search via Supabase RPC
    # Falls back to keyword search if the function isn't available
    payload = {
        "query_embedding": embedding,
        "match_threshold": 0.3,
        "match_count": limit
    }
    if category:
        payload["filter_category"] = category

    # Try vector search first
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/search_training",
        headers=headers,
        json=payload
    )

    if resp.status_code == 200:
        return resp.json()

    # Fallback: keyword + category filter via REST
    params = {"select": "id,session_date,title,primary_category,categories,summary,key_takeaways,scripts,objection_handling", "limit": limit}
    if category:
        params["categories"] = f"cs.{{\"{category}\"}}"
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/sales_training_sessions",
        headers=headers,
        params=params
    )
    return resp.json() if resp.status_code == 200 else []


def format_for_agent(results: list) -> str:
    """Format search results for use in an AI agent prompt."""
    if not results:
        return "No relevant training found."

    lines = []
    for r in results:
        lines.append(f"## {r.get('title')} ({r.get('session_date')})")
        lines.append(f"Category: {r.get('primary_category')}")
        if r.get("summary"):
            lines.append(f"Summary: {r['summary']}")
        if r.get("key_takeaways"):
            lines.append("Key takeaways:")
            for t in r["key_takeaways"]:
                lines.append(f"  - {t}")
        if r.get("scripts"):
            lines.append("Scripts:")
            for s in r["scripts"]:
                lines.append(f'  "{s}"')
        if r.get("objection_handling"):
            lines.append("Objection handling:")
            for o in r["objection_handling"]:
                lines.append(f"  Objection: {o.get('objection')}")
                lines.append(f"  Response:  {o.get('response')}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="What to search for")
    parser.add_argument("--category", choices=VALID_CATEGORIES, help="Filter by category")
    parser.add_argument("--limit", type=int, default=3, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    results = search(args.query, args.category, args.limit)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_for_agent(results))


if __name__ == "__main__":
    main()
