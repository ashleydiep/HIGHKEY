# Commands & Shortcuts Reference

All commands are typed directly in the Claude Code chat window.

---

## Data & Syncing

| Command | What it does |
|---------|-------------|
| `/sync` | Runs all data sync scripts (GHL, Google Ads, Google Ads Sheet, Gmail) and shows a results table |
| `/connect-data` | Guided Data layer builder — connects new services to Supabase, schedules syncs. Resumable. |
| `/connect-data status` | Shows what's connected, what's not, and what's scheduled. No changes made. |
| `/connect-data connect [SERVICE]` | Connect one specific service (e.g. `/connect-data connect Gmail`) |
| `/connect-data schedule syncs` | Set up nightly Routines to automate all syncs |

---

## Context & Session

| Command | What it does |
|---------|-------------|
| `/prime` | Start-of-session init — reads your context files, checks system status, tells you what to work on next |
| `/build-context` | Guided wizard to fill in your context files (personal info, companies, team, strategy, metrics, integrations) |

---

## Planning & Building

| Command | What it does |
|---------|-------------|
| `/create-plan [request]` | Creates a detailed implementation plan before building anything significant |
| `/implement [plan-path]` | Executes a plan step by step |

---

## Decisions

| Command | What it does |
|---------|-------------|
| `/decide [question]` | Log a business decision — records what you chose, why, and what you expected. Reviewed at 30 days. |
| `/activate-decision-engine` | Upgrades decision logging from file-based to full Supabase-backed engine (do this after Daily Brief is live) |

---

## System Health

| Command | What it does |
|---------|-------------|
| `/audit-system` | Checks your AI OS against current best practices — flags gaps, suggests improvements |

---

## Scheduling & Automation

| Command | What it does |
|---------|-------------|
| `/schedule` | Create or manage cloud Routines (recurring agents that run on a cron schedule — no machine needed) |

---

## Sync Scripts (run manually or via `/sync`)

Located in `scripts/sync/`. Can also be run directly in terminal.

| Script | What it syncs |
|--------|--------------|
| `scripts/sync/ghl.py` | GHL contacts, opportunities, notes → Supabase |
| `scripts/sync/google_ads.py` | Google Ads campaign performance (last 90 days) → Supabase |
| `scripts/sync/google_ads_sheet.py` | Google Ads tracking sheet (monthly summary) → Supabase |
| `scripts/sync/gmail.py` | Gmail emails (last 12 months, non-promotional) → Supabase with embeddings |

---

## Connected Services (Live via MCP — always available)

These don't need syncing — they're queried live in any conversation.

| Service | What you can ask |
|---------|-----------------|
| Google Calendar | Today's schedule, upcoming meetings, free/busy times |
| Google Drive | Find files, read documents, search Drive |
| Notion | Read pages, search notes, query databases |
| Gmail MCP | Read recent emails, search inbox live |

---

_Last updated: April 2026_
