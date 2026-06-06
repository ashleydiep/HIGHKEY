#!/usr/bin/env python3
"""
Calendar → GHL Contact Creator (Agent Attraction)
Watches Google Calendar for Calendly events from Michelle Wilson or Chad Cooley.
Event title format: "<Name> & Michelle Wilson" or "<Name> and Chad Cooley"

For each event:
- Extracts the prospect's name from the title
- Gets their email from the event attendees
- Creates a GHL contact if not already there, tagged "agent" and "agentnewsletter"
- Adds a note with their email + who they met with (recruited by context)

Usage:
  python3 calendar_to_ghl.py            # scan 7 days back/forward
  python3 calendar_to_ghl.py --days 30  # wider window
  python3 calendar_to_ghl.py --dry-run  # preview without creating
"""
import json
import re
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import requests
import anthropic
from agent_config import load_config

# ── Load agent config ─────────────────────────────────────────────────────────
CFG = load_config()

GHL_KEY      = CFG['ghl_api_key']
LOCATION_ID  = CFG['ghl_location_id']
ANTHROPIC_KEY = CFG['anthropic_api_key']
SUPABASE_URL = CFG['supabase_url']
SUPABASE_KEY = CFG['supabase_service_role_key']
GHL_TAGS     = CFG.get('ghl_tags', ['agent', 'agentnewsletter'])

GHL_BASE = 'https://rest.gohighlevel.com/v1'
GHL_HEADERS = {'Authorization': f'Bearer {GHL_KEY}', 'Content-Type': 'application/json'}
SB_HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates,return=minimal',
}

OAUTH_KEYS = Path(__file__).parents[2] / 'gcp-oauth.keys.json'
STATE_FILE = Path(__file__).parents[2] / f'data/sync-state/calendar_ghl_{CFG["agent_id"]}.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Token file: per-agent if setup.py ran calendar auth, otherwise shared default
_token_override = CFG.get('calendar_token_file')
TOKEN_FILE = Path(_token_override) if _token_override else Path(__file__).parents[2] / 'data/tokens/calendar_token.json'

# Build internal emails set from config
INTERNAL_EMAILS = set(e.lower() for e in CFG.get('my_emails', []) + CFG.get('internal_emails', []))

# Build recruiter name keywords from config for the title regex
# e.g. ["Michelle Wilson", "Chad Cooley"] → "michelle\s+wilson|chad\s+cooley"
_recruiter_pattern = '|'.join(
    r'\s+'.join(re.escape(w) for w in name.split())
    for name in CFG.get('recruiter_names', ['Michelle Wilson', 'Chad Cooley'])
)
TITLE_PATTERN = re.compile(
    rf'^(.+?)\s+(?:&|and)\s+({_recruiter_pattern})\s*$',
    re.IGNORECASE,
)


# ─── Google Calendar ──────────────────────────────────────────────────────────

def get_calendar_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_KEYS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def fetch_events(days: int) -> list:
    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
    time_max = (now + timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')

    all_events = []
    page_token = None
    while True:
        kwargs = dict(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=250,
        )
        if page_token:
            kwargs['pageToken'] = page_token
        result = service.events().list(**kwargs).execute()
        items = result.get('items', [])
        all_events.extend([e for e in items if e.get('status') != 'cancelled'])
        page_token = result.get('nextPageToken')
        if not page_token:
            break
    return all_events


def parse_event_title(title: str) -> Optional[Tuple[str, str]]:
    """
    Parse a Calendly-style title like "John Smith & Michelle Wilson".
    Returns (prospect_name, recruiter_name) or None if title doesn't match.
    """
    match = TITLE_PATTERN.match(title.strip())
    if not match:
        return None
    prospect_name = match.group(1).strip()
    recruiter_name = match.group(2).strip().title()
    return prospect_name, recruiter_name


def get_guest_emails(event: dict) -> list:
    """Return all attendee emails that aren't internal/Ashley/Michelle/Chad."""
    guests = []
    for a in event.get('attendees', []):
        email = (a.get('email') or '').lower().strip()
        if not email:
            continue
        if 'resource.calendar.google.com' in email:
            continue
        if email in INTERNAL_EMAILS:
            continue
        # Skip Chad Cooley by name if his email isn't in INTERNAL_EMAILS
        name = (a.get('displayName') or '').lower()
        if 'chad cooley' in name:
            continue
        guests.append({'email': email, 'name': (a.get('displayName') or '').strip()})
    return guests


def find_prospect_email(guests: list, prospect_name: str) -> Optional[dict]:
    """
    Find the guest whose email/name best matches the prospect name from the title.
    Tries display name match first, then checks if name tokens appear in the email address.
    Falls back to the first guest if no match found.
    """
    if not guests:
        return None
    if len(guests) == 1:
        return guests[0]

    name_tokens = [t.lower() for t in prospect_name.split() if len(t) > 1]

    # 1. Try display name exact/partial match (skip empty names)
    for guest in guests:
        display = guest['name'].lower().strip()
        if not display:
            continue
        if prospect_name.lower() in display or display in prospect_name.lower():
            return guest

    # 2. Try matching name tokens in email address
    best_guest = None
    best_score = 0
    for guest in guests:
        email_local = guest['email'].split('@')[0].lower().replace('.', ' ').replace('_', ' ').replace('-', ' ')
        score = sum(1 for token in name_tokens if token in email_local)
        if score > best_score:
            best_score = score
            best_guest = guest

    if best_score > 0:
        return best_guest

    # 3. Fall back to first guest
    return guests[0]


# ─── GHL ──────────────────────────────────────────────────────────────────────

def search_ghl_contact(email: str) -> Optional[dict]:
    resp = requests.get(
        f'{GHL_BASE}/contacts/',
        headers=GHL_HEADERS,
        params={'query': email, 'locationId': LOCATION_ID},
        timeout=15,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    contacts = resp.json().get('contacts', [])
    for c in contacts:
        if (c.get('email') or '').lower() == email.lower():
            return c
    return None


def create_ghl_contact(first_name: str, last_name: str, email: str) -> dict:
    payload = {
        'locationId': LOCATION_ID,
        'firstName': first_name,
        'lastName': last_name,
        'email': email,
        'source': 'Google Calendar',
        'tags': GHL_TAGS,
    }
    resp = requests.post(f'{GHL_BASE}/contacts/', headers=GHL_HEADERS, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get('contact', data)


def add_ghl_note(contact_id: str, body: str):
    resp = requests.post(
        f'{GHL_BASE}/contacts/{contact_id}/notes/',
        headers=GHL_HEADERS,
        json={'body': body},
        timeout=15,
    )
    resp.raise_for_status()


# ─── AI name splitting ────────────────────────────────────────────────────────

def split_name(full_name: str) -> Tuple[str, str]:
    """Split a full name into first and last. Uses Claude for ambiguous cases."""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ''
    if len(parts) == 2:
        return parts[0], parts[1]

    # 3+ parts — use Claude to split correctly (handles "Mary Jo Smith", "Jr.", etc.)
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=80,
        messages=[{
            'role': 'user',
            'content': (
                f'Split this full name into first and last name for a CRM.\n'
                f'Name: "{full_name}"\n'
                f'Return ONLY JSON: {{"first_name": "...", "last_name": "..."}}'
            ),
        }],
    )
    text = message.content[0].text.strip()
    start, end = text.find('{'), text.rfind('}') + 1
    parsed = json.loads(text[start:end])
    return parsed.get('first_name', parts[0]), parsed.get('last_name', ' '.join(parts[1:]))


# ─── Supabase meeting mapping ─────────────────────────────────────────────────

def save_meeting_mapping(title: str, ghl_contact_id: str, contact_name: str, event_date: str):
    """
    Persist meeting_title → GHL contact_id in Supabase.
    The Cloudflare Worker reads this table when a Fireflies webhook arrives
    to know exactly which contact to post the meeting note to.
    """
    row = {
        'meeting_title': title,
        'ghl_contact_id': ghl_contact_id,
        'ghl_contact_name': contact_name,
        'event_date': event_date,
    }
    try:
        resp = requests.post(
            f'{SUPABASE_URL}/rest/v1/meeting_contact_map',
            headers=SB_HEADERS,
            json=row,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f'  Warning: Could not save meeting mapping — {e}')


# ─── State tracking ───────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'processed_event_ids': [], 'contacts_created': 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Create GHL contacts from Michelle/Chad Calendly events')
    parser.add_argument('--days', type=int, default=7, help='Days back/forward to scan (default: 7)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without creating contacts')
    args = parser.parse_args()

    state = load_state()
    processed_ids = set(state.get('processed_event_ids', []))

    print(f'Fetching calendar events ({args.days} days back/forward)...')
    events = fetch_events(args.days)
    print(f'  Found {len(events)} events total')

    new_events = [e for e in events if e['id'] not in processed_ids]
    print(f'  {len(new_events)} unprocessed events to check\n')

    contacts_created = 0
    contacts_skipped = 0
    qualifying_events = 0

    for event in new_events:
        title = event.get('summary', '')
        start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))

        parsed = parse_event_title(title)
        if not parsed:
            processed_ids.add(event['id'])
            continue

        prospect_name, recruiter_name = parsed
        qualifying_events += 1

        # Get guest emails from the event attendees
        guests = get_guest_emails(event)
        all_guest_emails = [g['email'] for g in guests]

        print(f'Event: "{title}" ({start[:10]})')
        print(f'  Prospect: {prospect_name} | Recruited by: {recruiter_name}')
        print(f'  Guest email(s): {", ".join(all_guest_emails) or "(none found in attendees)"}')

        if not guests:
            print(f'  No guest email found in attendees — skipping\n')
            processed_ids.add(event['id'])
            continue

        # Match the prospect name from the title to the right attendee email
        primary_guest = find_prospect_email(guests, prospect_name)
        email = primary_guest['email']

        existing = search_ghl_contact(email)
        if existing:
            name = existing.get('contactName') or existing.get('firstName', email)
            contact_id = existing.get('id', '')
            print(f'  Already in GHL as "{name}" — adding new meeting date note')

            # Save mapping so Fireflies webhook knows which contact to update
            if not args.dry_run and contact_id:
                save_meeting_mapping(title, contact_id, name, start[:10])
                add_ghl_note(contact_id, f'New Meeting Date: {start[:10]}\nMeeting: {title}')

            contacts_skipped += 1
            processed_ids.add(event['id'])
            continue

        # Split prospect name into first/last
        first_name, last_name = split_name(prospect_name)
        full_name = f'{first_name} {last_name}'.strip()

        # Other people on the call (excluding the prospect themselves)
        others_on_call = [e for e in all_guest_emails if e != email]
        others_line = ', '.join(others_on_call) if others_on_call else '(none)'
        note_body = (
            f'Meeting: {title}\n'
            f'Date: {start[:10]}\n'
            f'Other recruiters/agents on the call: {others_line}\n'
            f'Source: Google Calendar (Calendly)'
        )

        if args.dry_run:
            print(f'  [DRY RUN] Would create: "{full_name}" <{email}> | tags: {GHL_TAGS}')
            print(f'  [DRY RUN] Note: {note_body}\n')
            contacts_created += 1
            processed_ids.add(event['id'])
            continue

        contact = create_ghl_contact(first_name, last_name, email)
        contact_id = contact.get('id') or ''

        if contact_id:
            try:
                add_ghl_note(contact_id, note_body)
            except Exception as e:
                print(f'  Warning: Could not add note — {e}')
            # Save mapping so Fireflies webhook can find this contact
            save_meeting_mapping(title, contact_id, full_name, start[:10])

        print(f'  Created: "{full_name}" <{email}> (id={contact_id}) | tags: {GHL_TAGS}\n')
        contacts_created += 1
        processed_ids.add(event['id'])

    # Persist state
    state['processed_event_ids'] = list(processed_ids)[-500:]
    state['contacts_created'] = state.get('contacts_created', 0) + contacts_created
    save_state(state)

    print(f'Done.')
    print(f'  Qualifying events ("<Name> & Michelle Wilson / Chad Cooley"): {qualifying_events}')
    print(f'  Contacts created: {contacts_created}')
    print(f'  Already in GHL (skipped): {contacts_skipped}')
    if args.dry_run:
        print('  [DRY RUN] No contacts were actually created.')


if __name__ == '__main__':
    main()
