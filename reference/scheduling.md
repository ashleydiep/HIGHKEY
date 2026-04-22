# Scheduling — Automating Your AI OS with Routines

> This guide explains how to make your AI OS run automatically — generating briefs, syncing data, and producing analyses on a schedule, even when your computer is off. As of April 2026, the feature is called **Routines** (formerly "Cloud Scheduled Tasks").

---

## The Vision

Your AI OS shouldn't need you to be sitting at your computer to work. A Daily Brief should land in your inbox every morning at 7am. Data should sync every hour. Weekly reviews should generate every Monday. All without you lifting a finger.

Claude Code's **Routines** make this possible. You define what you want to happen, when you want it to happen, and where Claude should run it. The rest is automatic.

See the official docs: https://code.claude.com/docs/en/routines.md

---

## What a Routine Is

A Routine is a cloud-hosted task that runs your Claude Code project on Anthropic's infrastructure. Your computer can be off, asleep, or across the world — your AI OS still runs on schedule.

**Routines can be triggered three ways:**

| Trigger | When It Runs | Use Case |
|---------|-------------|----------|
| **Schedule** | Hourly / daily / weekdays / weekly | Morning briefs, weekly reviews, data syncs |
| **API endpoint** | Whenever you POST to the Routine's URL | External integrations, webhook-driven workflows |
| **GitHub events** | On commit, PR, or push | Auto-regenerate docs, run tests, post summaries |

And a single Routine can **chain outputs** via MCP connectors — post to Slack, create Linear tickets, email summaries, update Notion pages.

---

## The Three Tiers of Automation

There are still three ways to schedule work, depending on your needs:

| Tier | Runs On | Computer Needed? | Survives Restart? | Min Interval | Best For |
|------|---------|-----------------|-------------------|-------------|----------|
| **Routines** (cloud) | Anthropic's servers | No | Yes | 1 hour | Daily briefs, weekly reviews, recurring syncs |
| **Desktop** | Your Mac/PC | Yes (must be awake) | Yes | 1 minute | Frequent local tasks, file processing |
| **`/loop`** | Your current session | Yes (session open) | No | 1 minute | Quick polling, temporary monitoring |

**For most people, Routines are the right choice.** Your computer can be off. Your AI OS still runs.

---

## Setting Up a Routine

### Step 1: Push Your Project to GitHub

Your AI OS needs to be in a GitHub repository. Routines clone from GitHub each run — this is how they access your CLAUDE.md, context files, and scripts.

```bash
# If you haven't already
git init
git add .
git commit -m "Initial AI OS setup"
git remote add origin https://github.com/your-username/your-ai-os.git
git push -u origin main
```

**Important:** Your `.env.local` file is gitignored (it contains API keys). Routines get their environment variables separately — see Step 3.

### Step 2: Create the Routine

**Option A: Via the web**
1. Go to https://claude.ai/code/routines
2. Click "Create new Routine"
3. Connect your GitHub repository
4. Write your prompt (what you want Claude to do)
5. Set the trigger (schedule, API, or GitHub)

**Option B: Via Claude Code CLI**
Run `/schedule` in your Claude Code session and follow the prompts.

### Step 3: Configure Environment Variables

Your API keys and tokens need to be set in the Routine environment (not your local `.env.local`):

1. In the Routine settings, find "Environment Variables"
2. Add each variable your AI OS needs (e.g., `ANTHROPIC_API_KEY`, `AIRTABLE_API_KEY`, `SLACK_BOT_TOKEN`)
3. These are encrypted and only accessible to your Routines

### Step 4: Attach MCP Connectors (Optional)

If your AI OS uses MCP connections (see `reference/mcp-guide.md`), attach them to your Routine. Routines support MCP connectors for services like Slack, Notion, Supabase, and others — so your automated tasks can read and write live data.

**New in April 2026:** A single Routine can chain MCP outputs. Example: "Read the AI OS context, generate a Daily Brief, post it to Slack #daily-brief, create a Notion page with the full analysis, and send me an email summary." All in one Routine.

### Step 5: Set the Trigger

**For scheduled Routines:**

| Schedule | When It Runs | Example Use |
|----------|-------------|-------------|
| **Hourly** | Every hour | Data syncs, monitoring |
| **Daily** | Once per day (you choose the time) | Morning brief, end-of-day review |
| **Weekdays** | Monday-Friday at your chosen time | Working-day briefs |
| **Weekly** | Once per week (you choose day and time) | Weekly review, strategic analysis |

**For API-triggered Routines:**
- Each Routine gets a unique webhook URL. POST to it from any external system.
- Useful for: "when a new deal lands in Airtable, generate a kickoff doc" or "when a form is submitted, run my qualification prompt."

**For GitHub-triggered Routines:**
- Trigger on commit, PR, or push events.
- Useful for: "regenerate the docs after every push to main" or "post a PR summary when a PR opens."

---

## What to Automate First

Start with the highest-value automations:

### 1. Daily Brief (Recommended First)

Your morning intelligence report, generated automatically before you wake up.

**Prompt example:**
```
Read all context files. Check connected data sources for yesterday's activity.
Generate a Daily Brief covering: financial position, sales pipeline, team activity,
client health, and today's recommended priorities. Post the summary to Slack #daily-brief
and save the full version to outputs/briefs/ with today's date.
```

### 2. Weekly Review

A deeper strategic analysis, generated every Monday morning.

**Prompt example:**
```
Read all context files and this week's daily briefs. Analyse trends across the week.
Generate a weekly review covering: progress against strategic priorities, team
performance patterns, client health trends, and focus areas for the coming week.
Save to outputs/analyses/ and post the top 3 findings to Slack.
```

### 3. Data Syncs

Keep your data fresh by syncing on a schedule.

**Prompt example:**
```
Run the data sync scripts in scripts/sync/ to pull the latest data from connected
services. Report any errors or data quality issues to Slack #ai-os-alerts.
```

---

## How This Connects to the Function Layer

Routines are the execution engine for your Function layer:

```
You BUILD a function (e.g., Daily Brief generation)
    |
    You SCHEDULE it as a Routine (e.g., daily at 7am on Anthropic's cloud)
    |
    It RUNS automatically, reading your Context + Data
    |
    Output lands in outputs/ (or your inbox, Slack, Notion, etc.)
```

Without Routines, your functions only run when you manually trigger them. With Routines, your AI OS works while you sleep.

---

## Limitations to Know

**Routines (cloud):**
- Clone from GitHub each run — they cannot access local files on your computer (like SQLite databases). If you need local data, use Desktop tasks instead, or store your data in a cloud service accessible via MCP.
- Minimum interval is 1 hour. For more frequent tasks, use Desktop or `/loop`.
- Require a Pro, Max, Team, or Enterprise Claude plan.
- Each run creates a fresh session — no memory of previous runs unless persisted to files in your repo.

**Desktop Scheduled Tasks:**
- Your computer must be on and awake. If it sleeps, tasks are skipped.
- Configured through Claude Desktop (Cowork) app, not the CLI.

**`/loop` Tasks:**
- Only run while your current Claude Code session is open.
- Disappear when you end the session.
- Best for temporary monitoring, not long-term automation.

---

## Getting Started

1. **Push your project to GitHub** if you haven't already
2. **Start with one Routine** — a Daily Brief is the highest-value automation
3. **Configure environment variables** in the Routine settings
4. **Set the schedule** and let it run for a few days
5. **Review the outputs** — refine your prompt based on what you get

The first time your Daily Brief lands in your inbox without you doing anything, you'll understand why this matters. That's the Function layer working autonomously.

---

_Automation turns your AI OS from a tool you use into a system that works for you. Start with one Routine. Expand from there._
