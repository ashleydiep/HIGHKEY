# /numbers — Daily KPI Entry

> Log today's numbers, see your MTD and YTD totals, and track progress toward targets.

---

## Setup

- Supabase URL: read from `SUPABASE_URL` in `.env.local`
- Supabase key: read from `SUPABASE_SERVICE_ROLE_KEY` in `.env.local`
- Table: `daily_kpis`

---

## Step 1 — Check if today already has an entry

Query Supabase for today's date:

```
GET /rest/v1/daily_kpis?date=eq.{TODAY}&select=*
```

- If a row exists: show the current values and ask "Want to update any of these?"
- If no row: proceed to Step 2

---

## Step 2 — Collect today's numbers

Ask for each metric below. Ask them all at once in a single message — don't ask one at a time. Format it as a numbered list so it's easy to reply to.

**SELLER ACTIVITY**
1. Contacts (dials made)
2. Leads (people who engaged)
3. Emails sent
4. Seller appts set
5. Seller appts met
6. FSBO preview set
7. FSBO met
8. FSBO listings taken
9. Listings from other sources
10. Total listings taken

**BUYER ACTIVITY**
11. Buyer appts set
12. Buyer appts met
13. Buyer contracts signed

**AGENT RECRUITING**
14. Agent contacts (dials to agents)
15. Discovery calls set
16. Discovery calls met
17. 3-ways set
18. 3-ways met
19. Verbals (agent committed to join)
20. Agents onboarded

**CLOSINGS**
21. Closings today

**CONTENT**
22. Stories posted (Instagram/Facebook)
23. Posts or Reels posted
24. YouTube videos posted

**NOTES**
25. Any notes for the day? (optional — press Enter to skip)

Accept replies in any format — e.g. "1: 45, 2: 3, 3: 10..." or just numbers in order. Parse intelligently.

---

## Step 3 — Save to Supabase

UPSERT the row:

```
POST /rest/v1/daily_kpis
Headers: Prefer: resolution=merge-duplicates
```

```json
{
  "date": "YYYY-MM-DD",
  "contacts": 0,
  "leads": 0,
  "emails": 0,
  "appts_set": 0,
  "appts_met": 0,
  "fsbo_preview_set": 0,
  "fsbo_met": 0,
  "fsbo_listing": 0,
  "listings_other": 0,
  "listings": 0,
  "buyer_appts_set": 0,
  "buyer_appts_met": 0,
  "buyer_contracts_signed": 0,
  "agent_contacts": 0,
  "agent_discoveries_set": 0,
  "agent_discoveries_met": 0,
  "agent_3ways_set": 0,
  "agent_3ways_met": 0,
  "agent_verbals": 0,
  "agent_onboarded": 0,
  "closings": 0,
  "stories_posted": 0,
  "posts_reels_posted": 0,
  "youtube_posted": 0,
  "notes": ""
}
```

---

## Step 4 — Show the summary

After saving, query MTD and YTD totals and display this report:

```
GET /rest/v1/daily_kpis?date=gte.{FIRST_OF_MONTH}&select=*
GET /rest/v1/daily_kpis?date=gte.{FIRST_OF_YEAR}&select=*
```

Display the following report:

---

### Today — {DATE}
| Metric | Today |
|--------|-------|
| Contacts | X |
| Leads | X |
| Emails | X |
| Seller Appts Set | X |
| Seller Appts Met | X |
| FSBO Preview Set | X |
| FSBO Met | X |
| FSBO Listings | X |
| Listings (Other) | X |
| Total Listings | X |
| Buyer Appts Set | X |
| Buyer Appts Met | X |
| Buyer Contracts Signed | X |
| Agent Contacts | X |
| Discoveries Set | X |
| Discoveries Met | X |
| 3-Ways Set | X |
| 3-Ways Met | X |
| Verbals | X |
| Agents Onboarded | X |
| Closings | X |
| Stories Posted | X |
| Posts/Reels Posted | X |
| YouTube Posted | X |

### MTD vs YTD
| Metric | MTD | YTD |
|--------|-----|-----|
| Contacts | X | X |
| Leads | X | X |
| Appts Set (Seller) | X | X |
| Appts Met (Seller) | X | X |
| Listings | X | X |
| Buyer Appts Set | X | X |
| Buyer Appts Met | X | X |
| Buyer Contracts | X | X |
| Closings | X | X |
| Agent Contacts | X | X |
| Discoveries Set | X | X |
| Discoveries Met | X | X |
| 3-Ways Set | X | X |
| 3-Ways Met | X | X |
| Verbals | X | X |
| Agents Onboarded | X | X |

### Key Ratios (YTD)
| Ratio | Value | Target |
|-------|-------|--------|
| Contacts → Appt Set | 1 in X | 1 in 25 |
| Appt Set → Listing | 1 in X | 1 in 5 |
| Appt Met → Listing | 1 in X | 1 in 2 |
| Contacts → Listing | 1 in X | — |
| Appts Met Rate | X% | — |

---

Compute ratios from raw totals. Round to whole numbers.

**Always end with:** "Numbers saved. 🔒 See you tomorrow."
