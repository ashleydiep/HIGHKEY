#!/usr/bin/env python3
"""GHL sync: contacts, opportunities, notes → Supabase."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

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

GHL_KEY = os.environ['GHL_PROAGENT_API_KEY']
LOCATION_ID = os.environ['GHL_PROAGENT_LOCATION_ID']
BASE = 'https://rest.gohighlevel.com/v1'
STATE_FILE = Path(__file__).parents[2] / 'data/sync-state/ghl.json'

PIPELINE_NAMES = {
    'okPDhRpZFpOyibTiHDcU': 'Agent Pipeline',
    'v1cUpUAhxumYVkXuhK22': 'Marketing Pipeline',
    '601one8uXUxoi9Hh315z': 'Real Estate Pipeline',
}

HEADERS = {'Authorization': f'Bearer {GHL_KEY}', 'Content-Type': 'application/json'}


def ghl_get(path: str) -> dict:
    url = path if path.startswith('http') else f'{BASE}{path}'
    url = url.replace('http://', 'https://')
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    return res.json()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'lastContactSync': None, 'lastOppSync': None, 'lastNoteSync': None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── contacts ─────────────────────────────────────────────────────────────────

def sync_contacts(since: Optional[str]):
    print('[contacts] starting...')
    db = get_client()
    total = 0
    url = f'{BASE}/contacts/?limit=100'
    if since:
        since_ms = int(datetime.fromisoformat(since.replace('Z', '+00:00')).timestamp() * 1000)
        url += f'&startAfter={since_ms}'

    while url:
        data = ghl_get(url)
        contacts = data.get('contacts', [])
        if not contacts:
            break

        rows = [
            {
                'source_id': c['id'],
                'location_id': c.get('locationId', LOCATION_ID),
                'first_name': c.get('firstName'),
                'last_name': c.get('lastName'),
                'full_name': c.get('contactName'),
                'email': c.get('email'),
                'phone': c.get('phone'),
                'contact_type': c.get('type'),
                'tags': c.get('tags', []),
                'source': c.get('source'),
                'city': c.get('city'),
                'state': c.get('state'),
                'country': c.get('country'),
                'assigned_to': c.get('assignedTo'),
                'dnd': c.get('dnd', False),
                'date_added': c.get('dateAdded'),
                'date_updated': c.get('dateUpdated'),
                'metadata': {'customFields': c.get('customField', [])},
                '_synced_at': now_iso(),
            }
            for c in contacts
        ]

        result = db.table('ghl_contacts').upsert(rows, on_conflict='source_id').execute()
        total += len(rows)
        print(f'[contacts] {total} upserted...')

        next_url = data.get('meta', {}).get('nextPageUrl')
        url = next_url.replace('http://', 'https://') if next_url else None

    print(f'[contacts] done — {total} synced')
    return total


# ─── opportunities ─────────────────────────────────────────────────────────────

def load_stage_names() -> dict:
    data = ghl_get('/pipelines/')
    stage_names = {}
    for pipeline in data.get('pipelines', []):
        for stage in pipeline.get('stages', []):
            stage_names[stage['id']] = stage['name']
    return stage_names


def sync_opportunities():
    print('[opportunities] starting...')
    db = get_client()
    stage_names = load_stage_names()
    total = 0

    for pipeline_id, pipeline_name in PIPELINE_NAMES.items():
        url = f'{BASE}/pipelines/{pipeline_id}/opportunities/?limit=100'
        while url:
            data = ghl_get(url)
            opps = data.get('opportunities', [])
            if not opps:
                break

            rows = [
                {
                    'source_id': o['id'],
                    'name': o.get('name'),
                    'pipeline_id': pipeline_id,
                    'pipeline_name': pipeline_name,
                    'stage_id': o.get('pipelineStageId'),
                    'stage_name': stage_names.get(o.get('pipelineStageId', '')),
                    'status': o.get('status'),
                    'monetary_value': o.get('monetaryValue', 0),
                    'contact_id': (o.get('contact') or {}).get('id'),
                    'contact_name': (o.get('contact') or {}).get('name'),
                    'contact_email': (o.get('contact') or {}).get('email'),
                    'contact_phone': (o.get('contact') or {}).get('phone'),
                    'contact_tags': (o.get('contact') or {}).get('tags', []),
                    'last_stage_change_at': o.get('lastStatusChangeAt'),
                    'created_at': o.get('createdAt'),
                    '_synced_at': now_iso(),
                }
                for o in opps
            ]

            db.table('ghl_opportunities').upsert(rows, on_conflict='source_id').execute()
            total += len(rows)
            print(f'[opportunities] {pipeline_name}: {total} total upserted...')

            next_url = data.get('meta', {}).get('nextPageUrl')
            url = next_url.replace('http://', 'https://') if next_url else None

    print(f'[opportunities] done — {total} synced')
    return total


# ─── notes ────────────────────────────────────────────────────────────────────

def sync_notes(since: Optional[str]):
    print('[notes] collecting contacts...')
    since_ms = int(datetime.fromisoformat(since.replace('Z', '+00:00')).timestamp() * 1000) if since else None

    # Collect contact IDs to check
    contact_ids = []
    url = f'{BASE}/contacts/?limit=100'
    while url:
        data = ghl_get(url)
        for c in data.get('contacts', []):
            if since_ms:
                updated_ms = c.get('lastActivity') or 0
                if updated_ms < since_ms:
                    continue
            contact_ids.append({'id': c['id'], 'name': c.get('contactName', '')})
        next_url = data.get('meta', {}).get('nextPageUrl')
        url = next_url.replace('http://', 'https://') if next_url else None

    print(f'[notes] scanning {len(contact_ids)} contacts...')
    all_notes = []

    for contact in contact_ids:
        try:
            data = ghl_get(f'/contacts/{contact["id"]}/notes/')
            for note in data.get('notes', []):
                body = (note.get('body') or '').strip()
                if body:
                    all_notes.append({
                        'source_id': note['id'],
                        'contact_id': contact['id'],
                        'contact_name': contact['name'],
                        'body': body,
                        'date_added': note.get('dateAdded'),
                    })
        except Exception:
            pass

    if not all_notes:
        print('[notes] no notes found')
        return 0

    # Skip notes already embedded in Supabase
    db = get_client()
    existing_ids = set()
    page_size = 1000
    offset = 0
    while True:
        result = db.table('ghl_notes').select('source_id').range(offset, offset + page_size - 1).execute()
        for row in result.data:
            existing_ids.add(row['source_id'])
        if len(result.data) < page_size:
            break
        offset += page_size

    new_notes = [n for n in all_notes if n['source_id'] not in existing_ids]
    print(f'[notes] {len(all_notes)} total, {len(existing_ids)} already synced, {len(new_notes)} new to embed')

    if not new_notes:
        print('[notes] all up to date')
        return 0

    print(f'[notes] embedding {len(new_notes)} notes...')
    total = 0

    import time
    for batch in chunk_list(new_notes, 10):
        embeddings = embed_batch([n['body'] for n in batch])
        time.sleep(3)
        rows = [
            {
                'source_id': n['source_id'],
                'contact_id': n['contact_id'],
                'contact_name': n['contact_name'],
                'body': n['body'],
                'metadata': {},
                'embedding': embeddings[i],
                'embedding_model': 'voyage-3-large',
                'date_added': n['date_added'],
                '_synced_at': now_iso(),
            }
            for i, n in enumerate(batch)
        ]
        db.table('ghl_notes').upsert(rows, on_conflict='source_id').execute()
        total += len(rows)
        print(f'[notes] {total}/{len(new_notes)} embedded and stored')

    print(f'[notes] done — {total} synced')
    return total


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print('=== GHL sync starting ===')
    state = load_state()
    now = now_iso()

    try:
        sync_contacts(state.get('lastContactSync'))
        state['lastContactSync'] = now
        save_state(state)

        sync_opportunities()
        state['lastOppSync'] = now
        save_state(state)

        sync_notes(state.get('lastNoteSync'))
        state['lastNoteSync'] = now
        save_state(state)

        print('=== GHL sync complete ===')
    except Exception as e:
        print(f'GHL sync failed: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
