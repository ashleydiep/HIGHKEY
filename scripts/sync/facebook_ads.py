#!/usr/bin/env python3
"""Facebook Ads sync: campaign performance (last 90 days) → Supabase."""
import os
import sys
import json
from datetime import datetime, timezone, timedelta, date
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
import requests

TOKEN_FILE = Path(__file__).parents[2] / 'data/tokens/meta_token.json'
AD_ACCOUNT_ID = os.environ['META_AD_ACCOUNT_ID']


def get_user_token() -> str:
    return json.loads(TOKEN_FILE.read_text())['user_long_token']


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def graph(path: str, params: dict, token: str) -> dict:
    params['access_token'] = token
    r = requests.get(f'https://graph.facebook.com/v19.0/{path}', params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def extract_action(actions: list, action_type: str) -> int:
    for a in (actions or []):
        if a.get('action_type') == action_type:
            return int(float(a.get('value', 0)))
    return 0


def sync_campaign_performance(days_back: int = 90):
    print(f'[facebook_ads] fetching last {days_back} days...')
    token = get_user_token()

    since = (date.today() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    until = date.today().strftime('%Y-%m-%d')

    data = graph(f'{AD_ACCOUNT_ID}/insights', {
        'level': 'adset',
        'fields': ','.join([
            'date_start',
            'campaign_id',
            'campaign_name',
            'adset_id',
            'adset_name',
            'impressions',
            'reach',
            'clicks',
            'spend',
            'cpc',
            'cpm',
            'ctr',
            'actions',
            'video_p25_watched_actions',
        ]),
        'time_range': json.dumps({'since': since, 'until': until}),
        'time_increment': 1,
        'limit': 500,
    }, token)

    rows = []
    all_data = data.get('data', [])

    # Handle pagination
    while data.get('paging', {}).get('next'):
        r = requests.get(data['paging']['next'], timeout=30)
        data = r.json()
        all_data.extend(data.get('data', []))

    print(f'[facebook_ads] {len(all_data)} daily adset rows found')

    for row in all_data:
        actions = row.get('actions', [])
        rows.append({
            'source_id': f'{row["date_start"]}_{row.get("adset_id", "")}',
            'date': row['date_start'],
            'campaign_id': row.get('campaign_id'),
            'campaign_name': row.get('campaign_name'),
            'adset_id': row.get('adset_id'),
            'adset_name': row.get('adset_name'),
            'impressions': int(row.get('impressions', 0)),
            'reach': int(row.get('reach', 0)),
            'clicks': int(row.get('clicks', 0)),
            'spend': float(row.get('spend', 0)),
            'cpc': float(row['cpc']) if row.get('cpc') else None,
            'cpm': float(row['cpm']) if row.get('cpm') else None,
            'ctr_pct': float(row['ctr']) if row.get('ctr') else None,
            'leads': extract_action(actions, 'lead'),
            'link_clicks': extract_action(actions, 'link_click'),
            'video_views': extract_action(actions, 'video_view'),
            '_synced_at': now_iso(),
        })

    return rows


def main():
    print('=== Facebook Ads sync starting ===')
    try:
        rows = sync_campaign_performance(days_back=90)

        if not rows:
            print('[facebook_ads] no data returned — account may have no active campaigns in this period')
            return

        db = get_client()
        for i in range(0, len(rows), 200):
            batch = rows[i:i+200]
            db.table('facebook_ads_performance').upsert(batch, on_conflict='source_id').execute()
            print(f'[facebook_ads] {min(i+200, len(rows))}/{len(rows)} upserted...')

        print(f'=== Facebook Ads sync complete — {len(rows)} rows ===')
    except Exception as e:
        print(f'Facebook Ads sync failed: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
