#!/usr/bin/env python3
"""Meta sync: Instagram post insights + account daily stats + Facebook Page posts → Supabase."""
import os
import sys
import json
from datetime import datetime, timezone, timedelta
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

PAGE_ID = os.environ['META_PAGE_ID']
IG_ID = os.environ['META_INSTAGRAM_ID']
APP_ID = os.environ['META_APP_ID']
APP_SECRET = os.environ['META_APP_SECRET']


def load_tokens() -> dict:
    return json.loads(TOKEN_FILE.read_text())


def refresh_page_token(tokens: dict) -> str:
    """Page tokens from /me/accounts are long-lived but not permanent. Refresh via user token."""
    r = requests.get('https://graph.facebook.com/v19.0/me/accounts', params={
        'access_token': tokens['user_long_token']
    })
    pages = r.json().get('data', [])
    for page in pages:
        if page['id'] == PAGE_ID:
            tokens['page_token'] = page['access_token']
            TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
            return page['access_token']
    return tokens.get('page_token', '')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def graph(path: str, params: dict, token: str) -> dict:
    params['access_token'] = token
    r = requests.get(f'https://graph.facebook.com/v19.0/{path}', params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# ─── Instagram posts ──────────────────────────────────────────────────────────

def sync_instagram_posts(page_token: str):
    print('[meta] syncing Instagram posts...')
    db = get_client()

    # Fetch recent media (last 100 posts)
    data = graph(f'{IG_ID}/media', {
        'fields': 'id,media_type,caption,permalink,thumbnail_url,timestamp',
        'limit': 100,
    }, page_token)

    media_items = data.get('data', [])
    print(f'[meta] {len(media_items)} Instagram posts found')

    rows = []
    for item in media_items:
        mid = item['id']

        # Get insights per post
        try:
            insights_data = graph(f'{mid}/insights', {
                'metric': 'impressions,reach,likes,comments,saves,shares',
            }, page_token)
            metrics = {m['name']: m['values'][0]['value'] for m in insights_data.get('data', [])}
        except Exception:
            metrics = {}

        impressions = metrics.get('impressions', 0)
        reach = metrics.get('reach', 0)
        likes = metrics.get('likes', 0)
        comments = metrics.get('comments', 0)
        saves = metrics.get('saves', 0)
        shares = metrics.get('shares', 0)
        engagement = round((likes + comments + saves + shares) / reach * 100, 2) if reach else None

        rows.append({
            'source_id': mid,
            'post_type': 'instagram',
            'media_type': item.get('media_type'),
            'caption': (item.get('caption') or '')[:2000],
            'permalink': item.get('permalink'),
            'thumbnail_url': item.get('thumbnail_url'),
            'timestamp': item.get('timestamp'),
            'impressions': impressions,
            'reach': reach,
            'likes': likes,
            'comments': comments,
            'saves': saves,
            'shares': shares,
            'engagement_rate': engagement,
            '_synced_at': now_iso(),
        })

    if rows:
        db.table('instagram_posts').upsert(rows, on_conflict='source_id').execute()
    print(f'[meta] {len(rows)} Instagram posts synced')
    return len(rows)


# ─── Instagram account daily stats ───────────────────────────────────────────

def sync_instagram_daily(page_token: str):
    print('[meta] syncing Instagram daily stats...')
    db = get_client()

    since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
    until = int(datetime.now(timezone.utc).timestamp())

    try:
        data = graph(f'{IG_ID}/insights', {
            'metric': 'impressions,reach,profile_views',
            'period': 'day',
            'since': since,
            'until': until,
        }, page_token)

        # Pivot metric arrays into per-day rows
        daily = {}
        for metric in data.get('data', []):
            name = metric['name']
            for entry in metric.get('values', []):
                date = entry['end_time'][:10]
                if date not in daily:
                    daily[date] = {'date': date}
                daily[date][name] = entry['value']

        # Get current follower count
        profile = graph(IG_ID, {'fields': 'followers_count'}, page_token)
        follower_count = profile.get('followers_count', 0)

        rows = []
        for date, stats in daily.items():
            rows.append({
                'source_id': f'ig-daily-{date}',
                'date': date,
                'impressions': stats.get('impressions', 0),
                'reach': stats.get('reach', 0),
                'profile_views': stats.get('profile_views', 0),
                'follower_count': follower_count,
                '_synced_at': now_iso(),
            })

        if rows:
            db.table('instagram_account_daily').upsert(rows, on_conflict='source_id').execute()
        print(f'[meta] {len(rows)} days of Instagram account stats synced')
        return len(rows)
    except Exception as e:
        print(f'[meta] Instagram daily stats skipped: {e}')
        return 0


# ─── Facebook Page posts ──────────────────────────────────────────────────────

def sync_facebook_posts(page_token: str):
    print('[meta] syncing Facebook Page posts...')
    db = get_client()

    data = graph(f'{PAGE_ID}/posts', {
        'fields': 'id,message,story,permalink_url,created_time',
        'limit': 50,
    }, page_token)

    posts = data.get('data', [])
    rows = []

    for post in posts:
        pid = post['id']
        try:
            insights = graph(f'{pid}/insights', {
                'metric': 'post_impressions,post_reach,post_reactions_like_total,post_comments,post_shares',
            }, page_token)
            metrics = {m['name']: m['values'][0]['value'] for m in insights.get('data', [])}
        except Exception:
            metrics = {}

        rows.append({
            'source_id': pid,
            'message': (post.get('message') or '')[:2000],
            'story': post.get('story'),
            'permalink': post.get('permalink_url'),
            'post_type': 'facebook',
            'created_time': post.get('created_time'),
            'impressions': metrics.get('post_impressions', 0),
            'reach': metrics.get('post_reach', 0),
            'likes': metrics.get('post_reactions_like_total', 0),
            'comments': metrics.get('post_comments', 0),
            'shares': metrics.get('post_shares', 0),
            '_synced_at': now_iso(),
        })

    if rows:
        db.table('facebook_page_posts').upsert(rows, on_conflict='source_id').execute()
    print(f'[meta] {len(rows)} Facebook posts synced')
    return len(rows)


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print('=== Meta sync starting ===')
    tokens = load_tokens()
    page_token = refresh_page_token(tokens)

    if not page_token:
        print('ERROR: No page token available', file=sys.stderr)
        sys.exit(1)

    try:
        sync_instagram_posts(page_token)
        sync_instagram_daily(page_token)
        sync_facebook_posts(page_token)
        print('=== Meta sync complete ===')
    except Exception as e:
        print(f'Meta sync failed: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
