# /decide — Decision Engine

Log a decision, respond to AI recommendations, review outcomes, or inspect patterns.

---

## Sub-commands

| Usage | What it does |
|---|---|
| `/decide` | Log a manual decision interactively |
| `/decide accept <rec_id> [<rec_id>...]` | Accept one or more AI recommendations |
| `/decide reject <rec_id> <category> [note]` | Reject a recommendation |
| `/decide reject <rec_id> later [N]` | Defer — resurface in N days (default 7) |
| `/decide pending` | List all open AI recommendations |
| `/decide review` | Walk decisions due for 30-day outcome review |
| `/decide patterns` | Show top decision patterns |

**Reject categories:** `disagree` · `no-time` · `redundant` · `wrong-context` · `later`

---

## Instructions

### `/decide` (no args) — log a manual decision

Run this to find similar past decisions first:

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.find_similar import find_similar_decisions
similar = find_similar_decisions('$ARGUMENTS') if '$ARGUMENTS' else []
for s in similar[:3]:
    print(f'  [{s.status}] {s.question[:70]} (similarity: {s.similarity:.0%})')
"
```

Ask Ashley:
1. **What's the decision?**
2. **Context** — what's the situation?
3. **Options considered**
4. **What you chose**
5. **Rationale** — why?
6. **Expected outcome**
7. **Confidence** — High / Medium / Low
8. **Company** — PROAGENT / COLLAB / High Key Solutions
9. **Tags** — e.g. `pricing`, `hiring`, `strategy`

Then log it:

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.log_decision import log_decision, LogDecisionInput
result = log_decision(LogDecisionInput(
    question='QUESTION',
    context='CONTEXT',
    options=['OPTION1', 'OPTION2'],
    chosen='CHOSEN',
    rationale='RATIONALE',
    expected_outcome='EXPECTED',
    confidence_score=0.8,
    tags=['TAG'],
    company='COMPANY',
    source='manual',
))
print(f'Logged: {result.id}')
if result.matches:
    print('Similar past decisions:')
    for m in result.matches:
        print(f'  [{m.status}] {m.question[:60]}')
"
```

Confirm: "Logged. I'll remind you to review this in 30 days."

---

### `/decide accept <rec_id>`

Parse the rec_id(s) from `$ARGUMENTS` and run:

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.record_response import record_recommendation_response, RecordResponseInput
result = record_recommendation_response(RecordResponseInput(
    rec_ids=['REC_ID'],
    action='accept',
))
print(f'Updated {result.updated} rec(s)')
for d in result.details:
    print(f'  {d.short_id}: accepted — 30-day review set')
if result.not_found:
    print(f'Not found: {result.not_found}')
"
```

---

### `/decide reject <rec_id> <category> [note]`

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.record_response import record_recommendation_response, RecordResponseInput
result = record_recommendation_response(RecordResponseInput(
    rec_ids=['REC_ID'],
    action='reject',
    category='CATEGORY',
    note='NOTE',
    surface_in_days=7,
))
print(f'Rejected: {result.details[0].short_id} ({result.details[0].reason_category})')
"
```

---

### `/decide pending`

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.db import rest
rows = rest('GET', 'decisions?source=eq.ai-recommendation&status=eq.pending&select=short_id,question,created_at&order=created_at.asc').json()
if not rows:
    print('No pending recommendations. Clean slate.')
else:
    print(f'{len(rows)} pending:\n')
    for r in rows:
        print(f'  [{r[\"short_id\"]}] {r[\"question\"]}')
        print(f'           since {r[\"created_at\"][:10]}')
"
```

---

### `/decide review`

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from datetime import datetime, timezone
from scripts.decisions.db import rest
now = datetime.now(timezone.utc).isoformat()
rows = rest('GET', f'decisions?outcome_assessed_at=lte.{now}&actual_outcome=is.null&status=in.(logged,accepted)&select=id,short_id,question,chosen,outcome_assessed_at&order=outcome_assessed_at.asc&limit=10').json()
if not rows:
    print('No decisions due for review.')
else:
    for r in rows:
        sid = r.get('short_id') or r['id'][:8]
        print(f'  [{sid}] {r[\"question\"]}')
        print(f'  Chose: {r.get(\"chosen\") or \"—\"}  |  Due: {r[\"outcome_assessed_at\"][:10]}\n')
"
```

For each, ask Ashley what actually happened, then record:

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.db import rest
rest('PATCH', 'decisions?id=eq.DECISION_ID', json={'actual_outcome': 'OUTCOME'})
print('Outcome recorded.')
"
```

---

### `/decide patterns`

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.decisions.db import rest
rows = rest('GET', 'decision_patterns?select=pattern_name,total_decisions,success_rate&order=total_decisions.desc&limit=10').json()
if not rows:
    print('No patterns yet — computed weekly from tagged decisions.')
else:
    for r in rows:
        rate = f\"{float(r['success_rate']):.0%}\" if r.get('success_rate') is not None else 'unrated'
        print(f'  {r[\"pattern_name\"]} — {r[\"total_decisions\"]} decisions, {rate} success')
"
```

---

## Telegram shortcuts (from your phone)

- `pending` — list open recs
- `accept rec_xxx` — accept
- `reject rec_xxx disagree` — disagree
- `reject rec_xxx later 3` — defer 3 days
