# Agent Attraction System — Deployment Guide

## For Ashley (first-time setup, already done)

Your webhook URL:
```
https://proagent-telegram.ashleydiepnm.workers.dev/fireflies/ashley_diep
```
Paste this into Fireflies.ai → Settings → Integrations → Webhooks → Trigger: Transcription completed.

---

## Adding a New Agent (takes ~10 minutes)

### Step 1 — Send them this package

Give the new agent the `scripts/automation/` folder. They need:
- Python 3.9+
- `pip3 install requests anthropic groq google-auth google-auth-oauthlib google-api-python-client`

### Step 2 — Run the setup wizard

```bash
cd scripts/automation
python3 setup.py
```

The wizard will ask for:
| Field | Where to find it |
|---|---|
| Full name | Their name |
| Recruiter names | "Michelle Wilson, Chad Cooley" (or whoever runs their calls) |
| Their emails | Personal + brokerage email |
| GHL API key | GHL → Settings → Integrations → API Key |
| GHL Location ID | GHL → Settings → Business Info → Location ID |
| Anthropic API key | console.anthropic.com → API Keys |
| Groq API key | console.groq.com → API Keys (free) |
| Telegram chat ID | Message @userinfobot on Telegram |
| Notification email | Where to send meeting summaries |

At the end it will print their **Fireflies webhook URL**:
```
https://proagent-telegram.ashleydiepnm.workers.dev/fireflies/{their_agent_id}
```

### Step 3 — Set up Fireflies.ai

1. Agent goes to fireflies.ai and creates a free account
2. Settings → Integrations → Google Calendar → Connect (uses their calendar)
3. Settings → Integrations → Webhooks → Add webhook:
   - URL: `https://proagent-telegram.ashleydiepnm.workers.dev/fireflies/{their_agent_id}`
   - Event: **Transcription completed**
4. Settings → Notifications → Email summaries → add Ashley's email as CC (optional)

### Step 4 — Verify it worked

Run a test to confirm the calendar scanner picks up their events:
```bash
python3 calendar_to_ghl.py --dry-run --days 30
```

You should see any `<Name> & Michelle Wilson` or `<Name> & Chad Cooley` events listed.

### Step 5 — Schedule the calendar scanner

Add to their daily sync or run manually each morning:
```bash
python3 scripts/automation/calendar_to_ghl.py
```

Or add to crontab (runs every day at 8am):
```
0 8 * * * cd /path/to/proagent-os && python3 scripts/automation/calendar_to_ghl.py
```

---

## How the system works (per agent)

```
Their Calendly → "<Name> & Michelle Wilson" event on Google Calendar
        ↓
calendar_to_ghl.py runs
  → Parses prospect name from event title
  → Finds their email from attendees
  → Checks GHL — creates contact if new, adds "New Meeting Date" note if existing
  → Saves mapping: event title → GHL contact ID in Supabase
        ↓
Call happens → Fireflies bot auto-joins (Zoom or Google Meet)
        ↓
Call ends → Fireflies hits:
  https://proagent-telegram.ashleydiepnm.workers.dev/fireflies/{agent_id}
        ↓
Worker looks up agent config from Supabase (their GHL key, chat ID, etc.)
Worker looks up GHL contact from the saved mapping
Worker posts meeting notes to GHL contact
Worker sends Telegram notification to agent
        ↓
Re-engagement (run weekly):
  python3 scripts/automation/reengage.py
  → Finds contacts untouched 60+ days
  → Drafts personalized message from their notes
  → Sends to agent's Telegram for review
```

---

## Each agent's unique URLs

| Agent | Fireflies Webhook |
|---|---|
| Ashley Diep | `.../fireflies/ashley_diep` |
| *(next agent)* | `.../fireflies/{their_agent_id}` |

---

## Troubleshooting

**Calendar scanner finds no events**
- Check that calendar events are titled exactly `<Name> & Michelle Wilson` or `<Name> and Chad Cooley`
- Run with `--days 90` to look back further

**Fireflies webhook not triggering**
- Confirm webhook URL is correct in Fireflies settings
- Check Cloudflare Worker logs: dashboard.cloudflare.com → Workers → proagent-telegram → Logs

**GHL contact not found after call**
- Run `calendar_to_ghl.py` first — it needs to create the mapping before the call
- Or check if the contact exists with a different email than what Fireflies captured

**Contact already exists, no new meeting date note**
- The script only adds the "New Meeting Date" note on a live run (not dry-run)
- Confirm you ran without `--dry-run`
