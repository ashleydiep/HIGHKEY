#!/usr/bin/env python3
"""One-time script to create the Agent Attraction SOP page in Notion Wiki."""
import json
import os
import requests

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
DATABASE_ID = "5b2922b5-425c-4414-9b02-c4ed3e370097"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def p(text):
    """Paragraph block."""
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def h1(text):
    return {"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def h2(text):
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def h3(text):
    return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def bullet(text, bold_prefix=None):
    if bold_prefix:
        return {
            "object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [
                {"type": "text", "text": {"content": bold_prefix}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": text}},
            ]},
        }
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def numbered(text):
    return {"object": "block", "type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def code(text):
    return {"object": "block", "type": "code", "code": {"rich_text": [{"type": "text", "text": {"content": text}}], "language": "plain text"}}


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


children = [
    h1("Agent Attraction System — SOP"),
    p("Owner: Ashley Diep  |  Last updated: 2026-05-15"),
    divider(),

    # ── What it does ──
    h2("What This System Does"),
    p("Automates the full agent attraction pipeline: from the moment a prospect books a call with Michelle Wilson or Chad Cooley, through the recorded conversation, to long-term re-engagement — with zero manual data entry."),
    p("Three main functions:"),
    bullet("Calendar Watcher — detects new Calendly bookings and creates/updates GHL contacts automatically"),
    bullet("AI Transcriber (Fireflies) — joins every Zoom/Google Meet call, transcribes it, posts structured notes to GHL, and sends a Telegram summary"),
    bullet("Re-engagement Scanner — finds contacts untouched 60+ days, drafts personalized messages with Claude, delivers them to Telegram for review before sending"),
    divider(),

    # ── How the flow works ──
    h2("How the Flow Works"),

    h3("Step 1 — Calendly Booking Detected"),
    p("When a prospect books a call, Calendly creates a Google Calendar event titled:"),
    code("John Smith & Michelle Wilson\nor\nJohn Smith and Chad Cooley"),
    p("The calendar_to_ghl.py script runs daily (cron at 8am) and:"),
    numbered("Scans Google Calendar for events matching the recruiter name pattern"),
    numbered("Extracts the prospect's name from the event title"),
    numbered("Finds the prospect's email from the calendar attendee list"),
    numbered("Checks GHL — if contact does not exist, creates it with tags: agent, agentnewsletter"),
    numbered("If contact already exists, adds a note: New Meeting Date: <date>"),
    numbered("Adds a note with any other guest emails: Other recruiters/agents on the call: <emails>"),
    numbered("Saves a mapping (event title → GHL contact ID) to Supabase so Fireflies can find the right contact later"),

    h3("Step 2 — Call Happens"),
    p("Fireflies.ai bot auto-joins the Zoom or Google Meet call via Google Calendar integration. No one needs to be on the call or invite the bot manually."),

    h3("Step 3 — Transcription Completed"),
    p("When the call ends, Fireflies processes the recording and sends a webhook to:"),
    code("https://proagent-telegram.ashleydiepnm.workers.dev/fireflies/{agent_id}"),
    p("The Cloudflare Worker:"),
    numbered("Loads the agent's credentials from Supabase (GHL API key, Telegram chat ID, etc.)"),
    numbered("Validates the meeting title matches the recruiter pattern"),
    numbered("Looks up the GHL contact using the Supabase mapping saved in Step 1"),
    numbered("Falls back to email search, then name search if the mapping is missing"),
    numbered("Posts a structured meeting note to the GHL contact profile"),
    numbered("Sends a Telegram message to the agent with summary, interest level, next best move, and action items"),

    h3("Step 4 — Re-engagement (Weekly)"),
    p("Run manually or on a weekly cron:"),
    code("python3 scripts/automation/reengage.py"),
    p("The script:"),
    numbered("Queries Supabase for all contacts where last_updated > 60 days ago"),
    numbered("Fetches that contact's notes from GHL"),
    numbered("Uses Claude Sonnet to draft a personalized re-engagement message and recommend the best channel (text, email, or call)"),
    numbered("Sends all drafts to the agent's Telegram for review before anything is sent"),
    divider(),

    # ── Setup process ──
    h2("Setup Process"),

    h3("Ashley's Setup (already done)"),
    bullet("Fireflies webhook URL: https://proagent-telegram.ashleydiepnm.workers.dev/fireflies/ashley_diep"),
    bullet("Paste this into Fireflies.ai → Settings → Integrations → Webhooks → Event: Transcription completed"),
    bullet("Calendar scanner runs via cron or manually: python3 scripts/automation/calendar_to_ghl.py"),

    h3("Adding a New Agent (~10 minutes)"),
    numbered("Give the agent the scripts/automation/ folder"),
    numbered("They install: pip3 install requests anthropic groq google-auth google-auth-oauthlib google-api-python-client"),
    numbered("They run: python3 setup.py — the wizard collects all credentials and registers them in Supabase"),
    numbered("Wizard outputs their personal webhook URL: .../fireflies/{their_agent_id}"),
    numbered("They paste that URL into Fireflies.ai → Settings → Integrations → Webhooks"),
    numbered("They create a free Fireflies account and connect Google Calendar"),

    h3("Credentials the Setup Wizard Collects"),
    bullet("Full name and recruiter names (e.g. Michelle Wilson, Chad Cooley)"),
    bullet("Their emails (personal + brokerage)"),
    bullet("GHL API key + Location ID"),
    bullet("Anthropic API key (console.anthropic.com)"),
    bullet("Groq API key — free at console.groq.com"),
    bullet("Telegram chat ID — message @userinfobot on Telegram"),
    divider(),

    # ── Key files ──
    h2("Key Files"),
    bullet("scripts/automation/calendar_to_ghl.py", "Calendar watcher: "),
    bullet("scripts/automation/reengage.py", "Re-engagement scanner: "),
    bullet("scripts/automation/meeting_transcriber.py", "Manual transcription fallback: "),
    bullet("scripts/automation/setup.py", "New agent setup wizard: "),
    bullet("scripts/automation/DEPLOY.md", "Full deployment guide: "),
    bullet("telegram-bot/src/index.js", "Cloudflare Worker (Fireflies webhook router): "),
    divider(),

    # ── Troubleshooting ──
    h2("Troubleshooting"),
    bullet("Calendar scanner finds no events — check event titles match exactly: <Name> & Michelle Wilson"),
    bullet("Fireflies webhook not triggering — check Cloudflare Worker logs: dashboard.cloudflare.com → Workers → proagent-telegram → Logs"),
    bullet("GHL contact not found after call — run calendar_to_ghl.py first to save the mapping before the call happens"),
    bullet("Re-engagement draft looks off — check the contact's GHL notes are populated with meeting history"),
]

payload = {
    "parent": {"database_id": DATABASE_ID},
    "properties": {
        "title": {
            "title": [{"type": "text", "text": {"content": "Agent Attraction System — SOP"}}]
        }
    },
    "children": children,
}

resp = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
if resp.status_code == 200:
    data = resp.json()
    print(f"✅ Notion SOP created!")
    print(f"   Page ID : {data['id']}")
    print(f"   URL     : {data.get('url', 'check Notion')}")
else:
    print(f"❌ Error {resp.status_code}: {resp.text}")
