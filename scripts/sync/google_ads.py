#!/usr/bin/env python3
"""Google Ads API sync: campaign performance → Supabase. Pulls last 90 days by default."""
import os
import sys
from datetime import datetime, timedelta, timezone, date
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

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

YAML_PATH = Path(__file__).parents[2] / 'google-ads.yaml'
CLIENT_ID = os.environ['GOOGLE_ADS_CLIENT_ID']


def get_ads_client():
    return GoogleAdsClient.load_from_storage(str(YAML_PATH))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sync_campaign_performance(days_back: int = 90):
    print(f'[google_ads] fetching last {days_back} days of campaign performance...')
    client = get_ads_client()
    service = client.get_service('GoogleAdsService')

    since = (date.today() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    until = date.today().strftime('%Y-%m-%d')

    query = f"""
        SELECT
            segments.date,
            campaign.id,
            campaign.name,
            campaign.status,
            ad_group.id,
            ad_group.name,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.average_cpc,
            metrics.average_cpm,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.cost_per_conversion,
            metrics.video_quartile_p25_rate,
            metrics.video_quartile_p50_rate,
            metrics.video_quartile_p75_rate,
            metrics.video_quartile_p100_rate
        FROM ad_group
        WHERE segments.date BETWEEN '{since}' AND '{until}'
          AND campaign.status != 'REMOVED'
          AND metrics.impressions > 0
        ORDER BY segments.date DESC, metrics.cost_micros DESC
    """

    rows = []
    try:
        response = service.search(customer_id=CLIENT_ID, query=query)
        for row in response:
            seg_date = row.segments.date
            campaign = row.campaign
            ad_group = row.ad_group
            m = row.metrics

            cost_usd = m.cost_micros / 1_000_000 if m.cost_micros else 0

            rows.append({
                'source_id': f'{seg_date}_{campaign.id}_{ad_group.id}',
                'date': seg_date,
                'campaign_id': str(campaign.id),
                'campaign_name': campaign.name,
                'campaign_status': campaign.status.name,
                'ad_group_id': str(ad_group.id),
                'ad_group_name': ad_group.name,
                'impressions': m.impressions,
                'views': None,
                'view_rate_pct': None,
                'clicks': m.clicks,
                'ctr_pct': round(m.ctr * 100, 4) if m.ctr else None,
                'cpc': round(m.average_cpc / 1_000_000, 4) if m.average_cpc else None,
                'cpm': round(m.average_cpm / 1_000_000, 4) if m.average_cpm else None,
                'cpv': None,
                'cost_micros': m.cost_micros,
                'cost_usd': round(cost_usd, 4),
                'conversions': m.conversions,
                'conversion_value': m.conversions_value,
                'cost_per_conversion': round(m.cost_per_conversion / 1_000_000, 4) if m.cost_per_conversion else None,
                'video_quartile_25_pct': round(m.video_quartile_p25_rate * 100, 2) if m.video_quartile_p25_rate else None,
                'video_quartile_50_pct': round(m.video_quartile_p50_rate * 100, 2) if m.video_quartile_p50_rate else None,
                'video_quartile_75_pct': round(m.video_quartile_p75_rate * 100, 2) if m.video_quartile_p75_rate else None,
                'video_quartile_100_pct': round(m.video_quartile_p100_rate * 100, 2) if m.video_quartile_p100_rate else None,
                '_synced_at': now_iso(),
            })

    except GoogleAdsException as ex:
        print(f'[google_ads] API error: {ex.error.code().name}')
        for error in ex.failure.errors:
            print(f'  {error.message}')
        raise

    print(f'[google_ads] {len(rows)} daily campaign rows fetched')
    return rows


def main():
    print('=== Google Ads sync starting ===')
    try:
        rows = sync_campaign_performance(days_back=90)
        if not rows:
            print('[google_ads] no data returned')
            return

        db = get_client()
        # Upsert in batches of 200
        for i in range(0, len(rows), 200):
            batch = rows[i:i+200]
            db.table('google_ads_performance').upsert(batch, on_conflict='source_id').execute()
            print(f'[google_ads] {min(i+200, len(rows))}/{len(rows)} upserted...')

        print(f'=== Google Ads sync complete — {len(rows)} rows ===')
    except Exception as e:
        print(f'Google Ads sync failed: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
