#!/usr/bin/env python3
"""
Google Calendar sync — pulls 7 days back + 14 days forward into Supabase.
Reuses the same GCP OAuth app as Gmail (adds calendar.readonly scope).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

env_file = Path(__file__).parents[2] / '.env.local'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
TOKEN_FILE = Path(__file__).parents[2] / 'data/tokens/calendar_token.json'
OAUTH_KEYS = Path(__file__).parents[2] / 'gcp-oauth.keys.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

import requests


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


def parse_event(evt: dict) -> dict:
    start = evt.get('start', {})
    end = evt.get('end', {})

    def parse_dt(d: dict):
        if 'dateTime' in d:
            return d['dateTime']
        if 'date' in d:
            return d['date'] + 'T00:00:00Z'
        return None

    attendees = [
        {'email': a.get('email'), 'name': a.get('displayName'), 'response': a.get('responseStatus')}
        for a in evt.get('attendees', [])
    ]

    return {
        'id': evt['id'],
        'calendar_id': 'primary',
        'title': evt.get('summary', '(No title)'),
        'description': evt.get('description'),
        'location': evt.get('location'),
        'start_time': parse_dt(start),
        'end_time': parse_dt(end),
        'all_day': 'date' in start and 'dateTime' not in start,
        'status': evt.get('status', 'confirmed'),
        'html_link': evt.get('htmlLink'),
        'attendees': attendees,
        'organizer': evt.get('organizer', {}).get('email'),
        'recurrence': evt.get('recurrence', []),
        '_synced_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }


def upsert_events(events: list):
    if not events:
        return
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=minimal',
    }
    resp = requests.post(f'{SUPABASE_URL}/rest/v1/calendar_events', headers=headers, json=events)
    resp.raise_for_status()


def main():
    print('Connecting to Google Calendar...')
    service = get_calendar_service()

    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    time_max = (now + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f'Fetching events from {time_min[:10]} to {time_max[:10]}...')
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
        all_events.extend([parse_event(e) for e in items if e.get('status') != 'cancelled'])

        page_token = result.get('nextPageToken')
        if not page_token:
            break

    print(f'  Found {len(all_events)} events — upserting to Supabase...')
    upsert_events(all_events)
    print(f'  Done. {len(all_events)} calendar events synced.')


if __name__ == '__main__':
    main()
