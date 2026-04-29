#!/usr/bin/env python3
"""Google Ads Sheet sync: monthly performance tracker → Supabase."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

env_file = Path(__file__).parents[2] / '.env.local'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parents[1]))
from utils.db import get_client

import warnings
warnings.filterwarnings('ignore')

import google.oauth2.credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SHEET_ID = '1p5FzjrS7png3Am19ckCjl7ZMKqfmT14zJy0MJFs1HwA'
OAUTH_KEYS = Path(__file__).parents[2] / 'gcp-oauth.keys.json'
GDRIVE_CREDS = Path(__file__).parents[2] / '.gdrive-credentials.json'

MONTH_ORDER = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


def get_drive_service():
    raw = json.loads(GDRIVE_CREDS.read_text())
    client = json.loads(OAUTH_KEYS.read_text())
    client = client.get('web', client.get('installed', {}))
    creds = google.oauth2.credentials.Credentials(
        token=raw['access_token'],
        refresh_token=raw['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client['client_id'],
        client_secret=client['client_secret'],
        scopes=[raw['scope']]
    )
    if not creds.valid:
        creds.refresh(Request())
    return build('drive', 'v3', credentials=creds)


def parse_num(val: str):
    """Parse currency/percentage strings to float. Returns None if empty/blank."""
    if not val or val.strip() in ('', ' ', '-'):
        return None
    val = val.strip().replace('$', '').replace(',', '').replace('%', '')
    try:
        return float(val)
    except ValueError:
        return None


def read_sheet(drive) -> list[dict]:
    content = drive.files().export(fileId=SHEET_ID, mimeType='text/csv').execute()
    lines = content.decode('utf-8').strip().splitlines()

    # Find header row (starts with 'Month')
    header_idx = next(i for i, l in enumerate(lines) if l.startswith('Month'))
    headers = [h.strip() for h in lines[header_idx].split(',')]

    rows = []
    current_year = datetime.now().year
    for line in lines[header_idx + 1:]:
        if not line.strip() or line.startswith(','):
            continue
        cells = [c.strip().strip('"') for c in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
        row = dict(zip(headers, cells))

        month = row.get('Month', '').strip()
        if month not in MONTH_ORDER or month == 'Total':
            continue

        spend = parse_num(row.get('Adspend (USD)', ''))
        if spend is None or spend == 0:
            continue  # skip empty months

        rows.append({
            'source_id': f'{current_year}-{month}',
            'month': month,
            'year': current_year,
            'adspend_usd': spend,
            'impressions': int(parse_num(row.get('Impressions', '')) or 0),
            'views': int(parse_num(row.get('Views', '')) or 0),
            'view_rate_pct': parse_num(row.get('View Rate', '')),
            'cpv': parse_num(row.get('CPV', '')),
            'cpm': parse_num(row.get('CPM', '')),
            'clicks': int(parse_num(row.get('Clicks', '')) or 0),
            'ctr_pct': parse_num(row.get('CTR', '')),
            'cpc': parse_num(row.get('CPC', '')),
            'listing_leads': int(parse_num(row.get('Listing leads', '')) or 0),
            'landing_page_pct': parse_num(row.get('LP%', '')),
            'cpl': parse_num(row.get('CPL', '')),
            'calendly_calls_scheduled': int(parse_num(row.get('Calendly calls scheduled', '')) or 0),
            'vcr_pct': parse_num(row.get('VCR-%', '')),
            'calendly_calls_conducted': int(parse_num(row.get('Calendly calls conducted', '')) or 0),
            'outbound_calls_connected': int(parse_num(row.get('Outbound calls connected', '')) or 0),
            'total_calls': int(parse_num(row.get('Total calls', '')) or 0),
            'sup_pct': parse_num(row.get('SUP-%', '')),
            'cost_per_call': parse_num(row.get('CPCall', '')),
            'listing_appointments': int(parse_num(row.get('Listing appointments', '')) or 0),
            'closed_listing_agreements': int(parse_num(row.get('Closed listing agreements', '')) or 0),
            'lead_cvr_pct': parse_num(row.get('L-CVR%', '')),
            'lc_pct': parse_num(row.get('LC%', '')),
            'booked_commission_usd': parse_num(row.get('Booked commission value', '')),
            'realized_commission_usd': parse_num(row.get('Realized commission', '')),
            'cpa': parse_num(row.get('CPA', '')),
            'realized_pl': parse_num(row.get('R-P/L', '')),
            'closed_pl': parse_num(row.get('C-P/L', '')),
            'b_roi_pct': parse_num(row.get('B-ROI', '')),
            'c_roi_pct': parse_num(row.get('C-ROI', '')),
            '_synced_at': datetime.now(timezone.utc).isoformat(),
        })

    return rows


def main():
    print('=== Google Ads Sheet sync starting ===')
    drive = get_drive_service()
    rows = read_sheet(drive)
    print(f'[ads] {len(rows)} active months found')

    if not rows:
        print('[ads] no data to sync')
        return

    db = get_client()
    db.table('google_ads_monthly').upsert(rows, on_conflict='source_id').execute()
    print(f'[ads] {len(rows)} months upserted to Supabase')
    print('=== Google Ads Sheet sync complete ===')


if __name__ == '__main__':
    main()
