#!/usr/bin/env python3
"""
Re-engagement Script
Finds GHL contacts that haven't been touched in N days,
uses Claude to draft personalized re-engagement messages based on their notes,
and sends them to Ashley via Telegram for review.

Usage:
  python3 reengage.py                # contacts untouched for 60+ days
  python3 reengage.py --days 90      # 90-day threshold
  python3 reengage.py --limit 5      # cap at 5 contacts per run
  python3 reengage.py --dry-run      # print drafts, don't send Telegram
"""
import json
import re
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import anthropic
from agent_config import load_config

EXCLUDED_TAGS = {'dead', 'listed', 'pastclient', 'buyer', 'socialmedia', 'agent'}

NOISE_PATTERNS = re.compile(
    r'^\s*(opened email campaign|email opened|sent a? ?text( message)?|'
    r'text sent|na|n/?a|no answer|no ans\.?|vm|voicemail|left vm|left voicemail|'
    r'system added note:)\s*$',
    re.IGNORECASE,
)


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', ' ', text).strip()


def is_meaningful_note(body: str) -> bool:
    """Return True if the note contains real conversation content."""
    if not body:
        return False
    clean = strip_html(body).strip()
    if len(clean) < 15:
        return False
    if NOISE_PATTERNS.match(clean):
        return False
    if clean.lower().startswith('system added note:'):
        return False
    return True


def has_excluded_tag(tags: list) -> bool:
    return bool(EXCLUDED_TAGS & {t.lower() for t in (tags or [])})

CFG = load_config()

GHL_KEY          = CFG['ghl_api_key']
LOCATION_ID      = CFG['ghl_location_id']
SUPABASE_URL     = CFG['supabase_url']
SUPABASE_KEY     = CFG['supabase_service_role_key']
ANTHROPIC_KEY    = CFG['anthropic_api_key']
TELEGRAM_TOKEN   = CFG.get('telegram_bot_token', '')
TELEGRAM_CHAT_ID = CFG.get('notification_telegram_chat_id')

GHL_BASE = 'https://rest.gohighlevel.com/v1'
GHL_HEADERS = {'Authorization': f'Bearer {GHL_KEY}', 'Content-Type': 'application/json'}
SB_HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
}


# ─── Supabase queries ─────────────────────────────────────────────────────────

def get_cold_contacts(days_threshold: int, limit: int) -> list:
    """Fetch cold contacts, pull a larger pool so tag/note filters still hit the limit."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_threshold)).isoformat()
    resp = requests.get(
        f'{SUPABASE_URL}/rest/v1/ghl_contacts',
        headers=SB_HEADERS,
        params={
            'select': 'source_id,full_name,first_name,last_name,email,phone,date_updated,tags',
            'date_updated': f'lt.{cutoff}',
            'order': 'date_updated.asc',
            'limit': str(limit * 10),
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def get_contact_notes(source_id: str) -> list:
    """Fetch all notes for a contact from Supabase."""
    resp = requests.get(
        f'{SUPABASE_URL}/rest/v1/ghl_notes',
        headers=SB_HEADERS,
        params={
            'select': 'body,date_added',
            'contact_id': f'eq.{source_id}',
            'order': 'date_added.desc',
            'limit': '10',
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ─── GHL live query ───────────────────────────────────────────────────────────

def get_live_contact_notes(contact_id: str) -> list:
    """Fetch notes directly from GHL API (catches notes not yet synced to Supabase)."""
    try:
        resp = requests.get(
            f'{GHL_BASE}/contacts/{contact_id}/notes/',
            headers=GHL_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        notes = resp.json().get('notes', [])
        return [{'body': n.get('body', ''), 'date_added': n.get('dateAdded', '')} for n in notes]
    except Exception:
        return []


# ─── AI message drafting ──────────────────────────────────────────────────────

def draft_reengage_message(contact: dict, notes: list) -> dict:
    """Use Claude to draft a personalized re-engagement message based on the contact's notes."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    name = contact.get('full_name') or contact.get('first_name') or 'Contact'
    last_updated = contact.get('date_updated', '')[:10]

    notes_text = ''
    if notes:
        notes_text = '\n\n'.join([
            f'[{n.get("date_added", "")[:10]}] {n.get("body", "").strip()}'
            for n in notes[:8]
            if n.get('body')
        ])
    else:
        notes_text = '(No notes on file)'

    prompt = f"""You are Ashley Diep's AI assistant. Ashley is a real estate agent in Houston reconnecting with a past contact.

Contact: {name}
Last touched: {last_updated or 'unknown'}

Notes from prior conversation:
{notes_text}

Draft a short re-engagement text Ashley can send from her phone.

Rules:
- Open with their WHY — the personal life reason behind their situation (divorce, growing family, retirement, financial pressure, visa, military move, moving abroad, etc.). Lead with empathy for their situation, not the transaction.
- Never open with real estate talk. The personal hook comes first.
- You CAN mention the market — but only as a supporting detail or incentive after the personal hook, not as the opener.
- Banned openers and phrases: "just checking in on your real estate", "are you still looking to sell", "interviewing agents", "I wanted to follow up on your home".
- Sound like a friend who genuinely remembered something specific about them.
- Tone: warm, casual, conversational. Like a real text — not a newsletter.
- Length: 2-3 sentences max. Short wins.
- If there's a specific life detail in the notes (visa situation, divorce, hard money loan, military schedule, retirement plan, moving abroad), anchor the message to THAT first.

Also suggest the best channel and urgency.

Return JSON:
{{
  "message": "the drafted message",
  "channel": "text|DM|call|email",
  "reasoning": "what life motivation you anchored to and why",
  "urgency": "low|medium|high"
}}"""

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=600,
        messages=[{'role': 'user', 'content': prompt}],
    )
    text = message.content[0].text.strip()
    start, end = text.find('{'), text.rfind('}') + 1
    return json.loads(text[start:end])


# ─── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(text: str):
    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
        json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'},
        timeout=15,
    )


def format_telegram_reengage(contact: dict, draft: dict, notes_count: int) -> str:
    name = contact.get('full_name') or contact.get('first_name') or 'Unknown'
    email = contact.get('email') or ''
    phone = contact.get('phone') or ''
    last_updated = contact.get('date_updated', '')[:10]
    channel = draft.get('channel', 'text').upper()
    urgency = draft.get('urgency', 'low').upper()
    message = draft.get('message', '')
    reasoning = draft.get('reasoning', '')

    contact_line = ' | '.join(filter(None, [email, phone]))

    return (
        f'🔄 *Re-engage: {name}*\n'
        f'📅 Last touched: {last_updated}\n'
        f'📞 {contact_line}\n'
        f'💬 Via: {channel} | Urgency: {urgency}\n'
        f'📝 Notes on file: {notes_count}\n\n'
        f'*Draft message:*\n_{message}_\n\n'
        f'_Why: {reasoning}_'
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Find cold contacts and draft re-engagement messages')
    parser.add_argument('--days', type=int, default=60, help='Days without touch to consider cold (default: 60)')
    parser.add_argument('--limit', type=int, default=10, help='Max contacts to process per run (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Print drafts without sending Telegram')
    args = parser.parse_args()

    print(f'\nRe-engagement Scanner')
    print(f'  Threshold : {args.days} days without contact')
    print(f'  Limit     : {args.limit} contacts\n')

    all_contacts = get_cold_contacts(args.days, args.limit)

    if not all_contacts:
        print(f'No contacts found untouched for {args.days}+ days.')
        return

    print(f'Pool: {len(all_contacts)} cold contacts — filtering by tags and notes...\n')

    if not args.dry_run:
        send_telegram(
            f'🔄 *Re-engagement Report*\n'
            f'Scanning {len(all_contacts)} cold contacts ({args.days}d threshold)...'
        )

    processed = 0
    skipped_tags = 0
    skipped_notes = 0

    for contact in all_contacts:
        if processed >= args.limit:
            break

        name = contact.get('full_name') or contact.get('first_name') or 'Unknown'
        source_id = contact.get('source_id', '')

        # Skip excluded tags
        if has_excluded_tag(contact.get('tags')):
            skipped_tags += 1
            continue

        # Get notes — try live GHL first, fall back to Supabase
        notes = get_live_contact_notes(source_id)
        if not notes:
            notes = get_contact_notes(source_id)

        # Filter to meaningful notes only
        meaningful = [n for n in notes if is_meaningful_note(n.get('body', ''))]
        if not meaningful:
            skipped_notes += 1
            continue

        print(f'Processing: {name} (last: {contact.get("date_updated", "")[:10]}, {len(meaningful)} real note(s))')

        try:
            draft = draft_reengage_message(contact, meaningful)
        except Exception as e:
            print(f'  Warning: Claude error for {name} — {e}')
            continue

        tg_msg = format_telegram_reengage(contact, draft, len(meaningful))

        if args.dry_run:
            print(f'\n--- {name} ---')
            print(f'Channel: {draft.get("channel")} | Urgency: {draft.get("urgency")}')
            print(f'Message: {draft.get("message")}')
            print(f'Why: {draft.get("reasoning")}')
        else:
            send_telegram(tg_msg)
            print(f'  Sent to Telegram')

        processed += 1

    print(f'\nDone. Processed {processed} contacts ({skipped_tags} skipped for tags, {skipped_notes} skipped — no real notes).')
    if not args.dry_run and processed > 0:
        send_telegram(f'✅ Re-engagement drafts complete ({processed} contacts). Review above and decide who to reach out to.')
    if not args.dry_run and processed == 0:
        send_telegram(f'🔍 Re-engagement scan complete — no qualifying contacts found ({args.days}d threshold, real notes required, excluded tags applied).')


if __name__ == '__main__':
    main()
