#!/usr/bin/env python3
"""Gmail sync: emails → Supabase with embeddings. Last 12 months, non-promotional."""
import base64
import email as email_lib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Load .env.local
env_file = Path(__file__).parents[2] / '.env.local'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parents[1]))
from utils.db import get_client
from utils.voyage import embed_batch, chunk_list

TOKEN_FILE = Path(__file__).parents[2] / 'data/tokens/gmail_token.json'
OAUTH_KEYS = Path(__file__).parents[2] / 'gcp-oauth.keys.json'
STATE_FILE = Path(__file__).parents[2] / 'data/sync-state/gmail.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Labels to skip — promotional/social noise
SKIP_LABELS = {'CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL', 'CATEGORY_UPDATES', 'SPAM', 'TRASH'}


def get_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_KEYS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'lastSync': None, 'totalSynced': 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def decode_body(payload: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    body = ''

    def extract(part):
        nonlocal body
        mime = part.get('mimeType', '')
        data = part.get('body', {}).get('data', '')
        if mime == 'text/plain' and data:
            body = base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
        elif mime.startswith('multipart/'):
            for sub in part.get('parts', []):
                extract(sub)

    extract(payload)
    return body.strip()


def parse_message(msg: dict) -> Optional[dict]:
    headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
    labels = msg.get('labelIds', [])

    # Skip promotional/social/spam
    if any(label in SKIP_LABELS for label in labels):
        return None

    from_raw = headers.get('from', '')
    from_name, from_email = '', from_raw
    if '<' in from_raw:
        parts = from_raw.split('<')
        from_name = parts[0].strip().strip('"')
        from_email = parts[1].rstrip('>')

    def parse_addresses(raw: str) -> list:
        return [e.strip() for e in raw.split(',') if e.strip()] if raw else []

    to_emails = parse_addresses(headers.get('to', ''))
    cc_emails = parse_addresses(headers.get('cc', ''))
    bcc_emails = parse_addresses(headers.get('bcc', ''))

    date_str = headers.get('date', '')
    date_sent = None
    if date_str:
        try:
            from email.utils import parsedate_to_datetime
            date_sent = parsedate_to_datetime(date_str).isoformat()
        except Exception:
            pass

    body = decode_body(msg.get('payload', {}))
    # Cap body at 8000 chars to keep embeddings meaningful
    body = body[:8000] if body else ''

    has_attachment = any(
        p.get('filename') for p in msg.get('payload', {}).get('parts', [])
    )

    return {
        'source_id': msg['id'],
        'thread_id': msg.get('threadId'),
        'from_email': from_email.lower().strip(),
        'from_name': from_name,
        'to_emails': to_emails,
        'cc_emails': cc_emails,
        'bcc_emails': bcc_emails,
        'subject': headers.get('subject', '(no subject)'),
        'snippet': msg.get('snippet', ''),
        'body': body,
        'date_sent': date_sent,
        'labels': labels,
        'has_attachment': has_attachment,
    }


def get_existing_ids(db) -> set:
    """Fetch all already-synced Gmail message IDs from Supabase."""
    existing = set()
    page_size = 1000
    offset = 0
    while True:
        result = db.table('gmail_emails').select('source_id').range(offset, offset + page_size - 1).execute()
        for row in result.data:
            existing.add(row['source_id'])
        if len(result.data) < page_size:
            break
        offset += page_size
    return existing


def sync_emails():
    print('[gmail] authenticating...')
    service = get_gmail_service()
    db = get_client()
    state = load_state()

    # After first run, use lastSync timestamp. First run defaults to 7 days back.
    if state.get('lastSync'):
        since = datetime.fromisoformat(state['lastSync']) - timedelta(hours=1)  # 1hr overlap for safety
        print(f'[gmail] incremental sync since {since.date()}')
    else:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        print(f'[gmail] first run — syncing last 7 days only')

    after_ts = int(since.timestamp())
    query = f'after:{after_ts} -category:promotions -category:social -category:updates'

    print(f'[gmail] fetching message IDs since {since.date()}...')
    existing_ids = get_existing_ids(db)
    print(f'[gmail] {len(existing_ids)} already synced')

    # Collect all message IDs from Gmail
    all_ids = []
    page_token = None
    while True:
        params = {'userId': 'me', 'q': query, 'maxResults': 500}
        if page_token:
            params['pageToken'] = page_token
        result = service.users().messages().list(**params).execute()
        messages = result.get('messages', [])
        all_ids.extend(m['id'] for m in messages)
        page_token = result.get('nextPageToken')
        if not page_token:
            break
        time.sleep(0.2)

    new_ids = [mid for mid in all_ids if mid not in existing_ids]
    print(f'[gmail] {len(all_ids)} total, {len(new_ids)} new to sync')

    if not new_ids:
        print('[gmail] all up to date')
        return 0

    # Fetch full messages and embed in batches of 10
    total = 0
    batch_messages = []

    for i, mid in enumerate(new_ids):
        try:
            msg = service.users().messages().get(userId='me', id=mid, format='full').execute()
            parsed = parse_message(msg)
            if parsed:
                batch_messages.append(parsed)
        except Exception as e:
            print(f'[gmail] skipping {mid}: {e}')

        # Embed and store every 20 messages
        if len(batch_messages) >= 20 or (i == len(new_ids) - 1 and batch_messages):
            embed_texts = [
                f"Subject: {m['subject']}\nFrom: {m['from_name']} <{m['from_email']}>\n\n{m['body']}"
                for m in batch_messages
            ]
            embeddings = embed_batch(embed_texts)
            time.sleep(35)  # Voyage free tier — conservative 35s gap

            rows = [
                {
                    **m,
                    'embedding': embeddings[j],
                    'embedding_model': 'voyage-3-large',
                    '_synced_at': now_iso(),
                }
                for j, m in enumerate(batch_messages)
            ]
            db.table('gmail_emails').upsert(rows, on_conflict='source_id').execute()
            total += len(rows)
            print(f'[gmail] {total}/{len(new_ids)} synced...')
            batch_messages = []

        # Respect Gmail API rate limits
        if i % 100 == 0 and i > 0:
            time.sleep(1)

    return total


def main():
    print('=== Gmail sync starting ===')
    state = load_state()

    try:
        total = sync_emails()
        state['lastSync'] = now_iso()
        state['totalSynced'] = state.get('totalSynced', 0) + total
        save_state(state)
        print(f'=== Gmail sync complete — {total} new emails synced ===')
    except Exception as e:
        print(f'Gmail sync failed: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
