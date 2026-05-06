# Plan: Daily Brief

**Created:** 2026-05-06
**Status:** Implemented
**Layer:** Function
**Request:** Build a daily brief script that pulls real data from Supabase and generates a morning intelligence report for Ashley

---

## Overview

### What This Accomplishes
A Python script (`scripts/daily_brief.py`) that queries Supabase for GHL pipeline data, yesterday's KPIs, Google Ads spend, and the latest Breakfast Club session, then uses Claude Opus to generate a structured morning brief saved to `outputs/briefs/YYYY-MM-DD.md`. A `/brief` slash command lets Ashley run it on demand.

### Why It Matters
Ashley's #1 priority is maximising revenue from PROAGENT and COLLAB. Without a daily brief, she has no consolidated view of her pipeline, activity numbers, and ad performance. This brief gives her an instant snapshot every morning so she knows exactly where to focus.

### Layer Dependencies
- Layer 2 (Context): Complete — personal-info, companies, strategy, integrations all populated
- Layer 3 (Data): Supabase connected — ghl_contacts, ghl_opportunities, daily_kpis, sales_training_sessions tables in place
- Layer 1 (AI OS): Claude Opus available via ANTHROPIC_API_KEY

---

## Current State
- No brief script or command exists
- Supabase has: ghl_contacts, ghl_opportunities, ghl_notes, daily_kpis, sales_training_sessions
- Google Ads sync exists but brief will pull from Supabase (already synced), not the Ads API directly
- outputs/briefs/ directory exists and is empty

---

## Proposed Changes

### Summary
- Create `scripts/daily_brief.py` — main brief generation script
- Create `.claude/commands/brief.md` — `/brief` slash command

### New Files

| File Path | Purpose |
|-----------|---------|
| `scripts/daily_brief.py` | Pulls data from Supabase, generates brief with Claude Opus, saves to outputs/briefs/ |
| `.claude/commands/brief.md` | `/brief` slash command — runs the script and displays the output |

---

## Design Decisions

1. **Claude Opus for generation**: Highest quality reasoning for strategic synthesis — matches CLAUDE.md recommendation for Daily Brief
2. **Pull from Supabase, not live APIs**: All data sources already sync to Supabase. Pulling from there is faster, cheaper, and doesn't require re-authenticating to 6 different services each morning
3. **Save as Markdown file**: Persists in outputs/briefs/ for future reference and weekly review
4. **Self-contained script**: Sources .env.local directly so it can run standalone or via Routine later

---

## Brief Sections

1. **Header** — Date, day of week
2. **Sales Pipeline** — GHL opportunities by pipeline (Real Estate, Agent, Marketing): count + value by stage
3. **Yesterday's KPIs** — Numbers from daily_kpis (contacts, appts set/met, listings, closings, buyer activity) — skips if no entry for yesterday
4. **MTD Totals + Key Ratios** — Contacts → Appt, Appt → Listing, running vs targets
5. **Latest Breakfast Club** — Most recent session's title + top 3 takeaways from sales_training_sessions
6. **Today's Focus** — Claude synthesises 3 recommended priorities based on pipeline gaps, KPI trends, and strategy.md priorities

---

## Step-by-Step Tasks

### Step 1: Create `scripts/daily_brief.py`

Write a complete Python script that:
- Sources credentials from `.env.local`
- Queries Supabase REST API for:
  - `ghl_opportunities`: open opportunities grouped by pipeline + stage
  - `daily_kpis`: yesterday's row + MTD aggregates (SUM of each column for current month)
  - `sales_training_sessions`: most recent session (title, key_takeaways)
- Calls Claude Opus with a system prompt grounded in Ashley's context (role, companies, strategy, targets)
- Passes all queried data into the prompt
- Saves generated brief to `outputs/briefs/YYYY-MM-DD.md`
- Prints the brief to stdout

**Files affected:**
- `scripts/daily_brief.py` (new)

### Step 2: Create `.claude/commands/brief.md`

Slash command that:
- Runs `scripts/daily_brief.py` via subprocess
- Displays the output
- Reports where the file was saved

**Files affected:**
- `.claude/commands/brief.md` (new)

---

## Validation Checklist
- [ ] Script runs without errors when executed directly
- [ ] Pulls real data from Supabase (not placeholders)
- [ ] Brief saved to outputs/briefs/ with correct date filename
- [ ] /brief command available in Claude Code
- [ ] Output covers all 6 sections

## Success Criteria
1. Running `python3 scripts/daily_brief.py` produces a complete brief in under 60 seconds
2. `/brief` command works in Claude Code session
3. Brief is specific to Ashley's actual pipeline and numbers — not generic

---

## Implementation Notes

**Implemented:** 2026-05-06

### Summary
Created `scripts/daily_brief.py` and `.claude/commands/brief.md`. Script runs successfully, pulls live GHL pipeline (109 agent opps, 149 real estate opps) and Supabase data, generates with Claude Opus, saves to `outputs/briefs/2026-05-06.md`.

### Deviations from Plan
- Fixed Python 3.9 compatibility: replaced `dict | None` type hints with `Optional[dict]` from typing
- Fixed f-string nested quote issue in pipeline formatter

### Issues Encountered
None — script runs cleanly and produces real data output.
