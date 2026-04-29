#!/usr/bin/env python3
"""YouTube Analytics sync: channel daily stats + video performance → Supabase."""
import os
import sys
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

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
]

# Each entry: (channel_id, channel_name, token_file)
CHANNELS = [
    (
        os.environ.get('YOUTUBE_CHANNEL_PROAGENT', ''),
        'Ashley Diep, ProAgent Real Estate',
        Path(__file__).parents[2] / 'data/tokens/youtube_token.json',
    ),
    (
        os.environ.get('YOUTUBE_CHANNEL_PERSONAL', ''),
        'Ashley Diep',
        Path(__file__).parents[2] / 'data/tokens/youtube_token_personal.json',
    ),
]


def get_services(token_file: Path):
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
    yt = build('youtube', 'v3', credentials=creds)
    yta = build('youtubeAnalytics', 'v2', credentials=creds)
    return yt, yta


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ─── Channel daily stats ──────────────────────────────────────────────────────

def sync_channel_daily(yta, channel_id: str, channel_name: str, days_back: int = 90):
    since = (date.today() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    until = date.today().strftime('%Y-%m-%d')

    try:
        r = yta.reports().query(
            ids=f'channel=={channel_id}',
            startDate=since,
            endDate=until,
            metrics='views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares',
            dimensions='day',
            sort='day',
        ).execute()
    except Exception as e:
        print(f'  [youtube] daily stats error for {channel_name}: {e}')
        return 0

    headers = [h['name'] for h in r.get('columnHeaders', [])]
    rows = []
    for row in r.get('rows', []):
        d = dict(zip(headers, row))
        rows.append({
            'source_id': f'{channel_id}-{d["day"]}',
            'channel_id': channel_id,
            'channel_name': channel_name,
            'date': d['day'],
            'views': int(d.get('views', 0)),
            'watch_time_minutes': int(d.get('estimatedMinutesWatched', 0)),
            'avg_view_duration_seconds': d.get('averageViewDuration'),
            'impressions': None,
            'impression_ctr_pct': None,
            'subscribers_gained': int(d.get('subscribersGained', 0)),
            'subscribers_lost': int(d.get('subscribersLost', 0)),
            'likes': int(d.get('likes', 0)),
            'comments': int(d.get('comments', 0)),
            'shares': int(d.get('shares', 0)),
            '_synced_at': now_iso(),
        })

    if rows:
        get_client().table('youtube_channel_daily').upsert(rows, on_conflict='source_id').execute()
    print(f'  [youtube] {channel_name}: {len(rows)} days synced')
    return len(rows)


# ─── Video stats ──────────────────────────────────────────────────────────────

def sync_videos(yt, yta, channel_id: str, channel_name: str):
    # Get all videos for this channel
    videos = []
    next_page = None
    while True:
        params = dict(part='snippet', channelId=channel_id, maxResults=50, type='video')
        if next_page:
            params['pageToken'] = next_page
        r = yt.search().list(**params).execute()
        for item in r.get('items', []):
            if item['id'].get('videoId'):
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'published_at': item['snippet']['publishedAt'],
                })
        next_page = r.get('nextPageToken')
        if not next_page:
            break

    if not videos:
        print(f'  [youtube] {channel_name}: no videos found')
        return 0

    # Get video durations
    vid_ids = [v['video_id'] for v in videos]
    for i in range(0, len(vid_ids), 50):
        batch = vid_ids[i:i+50]
        details = yt.videos().list(part='contentDetails', id=','.join(batch)).execute()
        duration_map = {}
        for item in details.get('items', []):
            dur = item['contentDetails']['duration']  # ISO 8601 e.g. PT4M13S
            import re
            h = int((re.search(r'(\d+)H', dur) or [0, 0])[1] or 0)
            m = int((re.search(r'(\d+)M', dur) or [0, 0])[1] or 0)
            s = int((re.search(r'(\d+)S', dur) or [0, 0])[1] or 0)
            duration_map[item['id']] = h * 3600 + m * 60 + s
        for v in videos:
            if v['video_id'] in duration_map:
                v['duration_seconds'] = duration_map[v['video_id']]

    # Get analytics per video
    rows = []
    for vid in videos:
        try:
            r = yta.reports().query(
                ids=f'channel=={channel_id}',
                startDate='2020-01-01',
                endDate=date.today().strftime('%Y-%m-%d'),
                metrics='views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained',
                filters=f'video=={vid["video_id"]}',
            ).execute()
        except Exception:
            continue

        headers = [h['name'] for h in r.get('columnHeaders', [])]
        if not r.get('rows'):
            continue
        d = dict(zip(headers, r['rows'][0]))

        rows.append({
            'source_id': f'{channel_id}-{vid["video_id"]}',
            'channel_id': channel_id,
            'channel_name': channel_name,
            'video_id': vid['video_id'],
            'title': vid['title'],
            'published_at': vid['published_at'],
            'duration_seconds': vid.get('duration_seconds'),
            'views': int(d.get('views', 0)),
            'watch_time_minutes': int(d.get('estimatedMinutesWatched', 0)),
            'avg_view_duration_seconds': d.get('averageViewDuration'),
            'avg_view_pct': d.get('averageViewPercentage'),
            'impressions': None,
            'impression_ctr_pct': None,
            'likes': int(d.get('likes', 0)),
            'comments': int(d.get('comments', 0)),
            'shares': int(d.get('shares', 0)),
            'subscribers_gained': int(d.get('subscribersGained', 0)),
            '_synced_at': now_iso(),
        })

    if rows:
        get_client().table('youtube_videos').upsert(rows, on_conflict='source_id').execute()
    print(f'  [youtube] {channel_name}: {len(rows)} videos synced')
    return len(rows)


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print('=== YouTube sync starting ===')

    for channel_id, channel_name, token_file in CHANNELS:
        if not channel_id or not token_file.exists():
            continue
        print(f'\n[youtube] syncing {channel_name}...')
        yt, yta = get_services(token_file)
        sync_channel_daily(yta, channel_id, channel_name)
        sync_videos(yt, yta, channel_id, channel_name)

    print('\n=== YouTube sync complete ===')


if __name__ == '__main__':
    main()
