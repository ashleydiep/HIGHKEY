#!/usr/bin/env python3
"""
Daily Brief — Ashley Diep / ProAgent AI OS
Pulls GHL pipeline, KPIs, Breakfast Club, and weekly targets from Supabase,
generates a morning intelligence report with Claude Opus,
and saves it to outputs/briefs/YYYY-MM-DD.md
"""

import os
import sys
import json
import requests
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

MODE = "evening" if "--mode=evening" in sys.argv else "morning"

# ── Credentials ───────────────────────────────────────────────────────────────
env_file = Path(__file__).parents[1] / '.env.local'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
ANTHROPIC_KEY = os.environ['ANTHROPIC_API_KEY']

SB_HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
}

OUTPUTS_DIR  = Path(__file__).parents[1] / 'outputs' / 'briefs'
TARGETS_DIR  = Path(__file__).parents[1] / 'data' / 'weekly-targets'
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

TODAY          = date.today()
YESTERDAY      = TODAY - timedelta(days=1)
FIRST_OF_MONTH = TODAY.replace(day=1)
WEEK_START     = TODAY - timedelta(days=TODAY.weekday())
WEEK_KEY       = TODAY.strftime('%Y-W%V')


# ── Supabase helpers ──────────────────────────────────────────────────────────
def sb_get(table: str, params: dict) -> list:
    resp = requests.get(
        f'{SUPABASE_URL}/rest/v1/{table}',
        headers={**SB_HEADERS, 'Prefer': 'count=none'},
        params=params, timeout=15,
    )
    if resp.status_code not in (200, 206):
        print(f'  Supabase error ({table}): {resp.status_code} {resp.text[:200]}')
        return []
    return resp.json()


# ── Data pulls ────────────────────────────────────────────────────────────────
def _cal_get(params: list) -> list:
    resp = requests.get(
        f'{SUPABASE_URL}/rest/v1/calendar_events',
        headers={**SB_HEADERS, 'Prefer': 'count=none'},
        params=params,
        timeout=15,
    )
    return resp.json() if resp.ok else []


def get_todays_events() -> list:
    return _cal_get([
        ('start_time', f'gte.{TODAY}T00:00:00Z'),
        ('start_time', f'lte.{TODAY}T23:59:59Z'),
        ('select', 'title,start_time,end_time,location,all_day'),
        ('order', 'start_time.asc'),
    ])


def get_upcoming_events(days: int = 3) -> list:
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    end = (TODAY + timedelta(days=days)).isoformat()
    return _cal_get([
        ('start_time', f'gte.{tomorrow}T00:00:00Z'),
        ('start_time', f'lte.{end}T23:59:59Z'),
        ('select', 'title,start_time,location'),
        ('order', 'start_time.asc'),
        ('limit', '10'),
    ])


def get_pipeline() -> dict:
    rows = sb_get('ghl_opportunities', {
        'select': 'pipeline_name,stage_name,monetary_value,status',
        'status': 'eq.open',
        'order': 'pipeline_name.asc,stage_name.asc',
    })
    pipelines = {}
    for r in rows:
        p = r.get('pipeline_name') or 'Unknown'
        s = r.get('stage_name') or 'Unknown'
        v = float(r.get('monetary_value') or 0)
        pipelines.setdefault(p, {}).setdefault(s, {'count': 0, 'value': 0})
        pipelines[p][s]['count'] += 1
        pipelines[p][s]['value'] += v
    return pipelines


def get_hot_sellers() -> list:
    priority_stages = {'Apt Set', 'Apt Attended-Not Signed', 'Apt Attended - Not Signed', 'Listing Taken'}

    # Pull by priority stages
    stage_rows = sb_get('ghl_opportunities', {
        'select': 'contact_name,contact_phone,stage_name,monetary_value,last_stage_change_at,created_at',
        'pipeline_name': 'eq.Real Estate Pipeline',
        'status': 'eq.open',
        'order': 'last_stage_change_at.desc',
    })
    stage_hits = [r for r in stage_rows if r.get('stage_name') in priority_stages]

    # Pull hot-30 tagged contacts not already in stage_hits
    tag_rows = sb_get('ghl_contacts', {
        'select': 'full_name,phone,tags,date_updated',
        'tags': 'cs.{"hot-30"}',
        'order': 'date_updated.desc',
    })
    stage_names = {r.get('contact_name') for r in stage_hits}
    tag_hits = [r for r in tag_rows if r.get('full_name') not in stage_names]

    results = []
    for r in stage_hits:
        days_ago = ''
        try:
            changed = datetime.fromisoformat((r.get('last_stage_change_at') or '').replace('Z', '+00:00'))
            days_ago = f'{(datetime.now(changed.tzinfo) - changed).days}d ago'
        except Exception:
            pass
        results.append({
            'name': r.get('contact_name') or 'Unknown',
            'phone': r.get('contact_phone') or '',
            'stage': r.get('stage_name') or '',
            'value': float(r.get('monetary_value') or 0),
            'last_activity': days_ago,
            'source': 'stage',
        })

    for r in tag_hits:
        days_ago = ''
        try:
            updated = datetime.fromisoformat((r.get('date_updated') or '').replace('Z', '+00:00'))
            days_ago = f'{(datetime.now(updated.tzinfo) - updated).days}d ago'
        except Exception:
            pass
        results.append({
            'name': r.get('full_name') or 'Unknown',
            'phone': r.get('phone') or '',
            'stage': 'hot-30 tag',
            'value': 0,
            'last_activity': days_ago,
            'source': 'tag',
        })

    return results


def get_closed_deals() -> dict:
    rows = sb_get('ghl_opportunities', {
        'select': 'pipeline_name,monetary_value,last_stage_change_at',
        'status': 'eq.won',
        'last_stage_change_at': f'gte.{FIRST_OF_MONTH.isoformat()}',
    })
    ytd_rows = sb_get('ghl_opportunities', {
        'select': 'pipeline_name,monetary_value',
        'status': 'eq.won',
        'last_stage_change_at': f'gte.{TODAY.replace(month=1, day=1).isoformat()}',
    })
    mtd_count = len(rows)
    mtd_value = sum(float(r.get('monetary_value') or 0) for r in rows)
    ytd_count = len(ytd_rows)
    ytd_value = sum(float(r.get('monetary_value') or 0) for r in ytd_rows)
    return {
        'mtd_count': mtd_count, 'mtd_value': mtd_value,
        'ytd_count': ytd_count, 'ytd_value': ytd_value,
    }


def get_yesterday_kpis() -> Optional[dict]:
    rows = sb_get('daily_kpis', {'date': f'eq.{YESTERDAY}', 'select': '*'})
    return rows[0] if rows else None


def get_mtd_kpis() -> dict:
    fields = (
        'contacts,leads,emails,appts_set,appts_met,'
        'fsbo_preview_set,fsbo_met,fsbo_listing,listings_other,listings,'
        'buyer_appts_set,buyer_appts_met,buyer_contracts_signed,closings,'
        'agent_contacts,agent_discoveries_set,agent_discoveries_met,'
        'agent_3ways_set,agent_3ways_met,agent_verbals,agent_onboarded,'
        'stories_posted,posts_reels_posted,youtube_posted'
    )
    rows = sb_get('daily_kpis', {'date': f'gte.{FIRST_OF_MONTH}', 'select': fields})
    totals = {f: 0 for f in fields.split(',')}
    for r in rows:
        for k in totals:
            totals[k] += r.get(k) or 0
    return totals


def get_wtd_kpis() -> dict:
    fields = (
        'contacts,appts_set,appts_met,listings,closings,'
        'buyer_appts_set,buyer_appts_met,buyer_contracts_signed,'
        'agent_contacts,agent_discoveries_set,agent_discoveries_met,'
        'agent_3ways_set,agent_3ways_met,agent_verbals,agent_onboarded,'
        'stories_posted,posts_reels_posted,youtube_posted'
    )
    rows = sb_get('daily_kpis', {'date': f'gte.{WEEK_START}', 'select': fields})
    totals = {f: 0 for f in fields.split(',')}
    for r in rows:
        for k in totals:
            totals[k] += r.get(k) or 0
    return totals


def get_latest_bclub() -> Optional[dict]:
    rows = sb_get('sales_training_sessions', {
        'select': 'session_date,title,summary,key_takeaways',
        'order': 'session_date.desc',
        'limit': '1',
    })
    return rows[0] if rows else None


def get_weekly_targets() -> Optional[dict]:
    path = TARGETS_DIR / f'{WEEK_KEY}.json'
    if path.exists():
        return json.loads(path.read_text())
    return None


def get_lead_followup_status() -> dict:
    """Read lead follow-up state: pending note approvals + recent outbound activity."""
    result = {
        'pending_approvals': [],   # leads who replied, notes waiting in Telegram
        'texted_recently': [],     # leads texted in last 7 days
        'total_in_repingqueue': 0, # leads being tracked for 60-day re-pings
    }

    # Pending Telegram approvals from Supabase
    try:
        rows = sb_get('pending_notes', {
            'select': 'contact_name,interest_level,next_step,created_at',
            'status': 'eq.pending',
            'order':  'created_at.desc',
        })
        result['pending_approvals'] = rows
    except Exception:
        pass

    # Recent outbound texts from Supabase (durable record)
    try:
        cutoff_7d  = (datetime.now() - timedelta(days=7)).isoformat()
        cutoff_60d = (datetime.now() - timedelta(days=60)).isoformat()
        recent_rows = sb_get('outbound_sms_log', {
            'select': 'contact_name,sent_at,priority',
            'sent_at': f'gte.{cutoff_7d}',
            'order': 'sent_at.desc',
        })
        result['texted_recently'] = recent_rows
        queue_rows = sb_get('outbound_sms_log', {
            'select': 'contact_id',
            'sent_at': f'gte.{cutoff_60d}',
        })
        # Unique contacts in the 60-day window = active re-ping queue size
        result['total_in_repingqueue'] = len({r['contact_id'] for r in queue_rows})
    except Exception:
        # Fall back to local state file if Supabase table doesn't exist yet
        try:
            state_file = Path(__file__).parents[1] / 'data/sync-state/lead_followup.json'
            if state_file.exists():
                state = json.loads(state_file.read_text())
                outbound = state.get('outbound_sent', {})
                cutoff_7d_s  = (datetime.now() - timedelta(days=7)).isoformat()
                cutoff_60d_s = (datetime.now() - timedelta(days=60)).isoformat()
                for contact_id, sent_at in outbound.items():
                    if sent_at > cutoff_7d_s:
                        result['texted_recently'].append({'contact_id': contact_id, 'sent_at': sent_at})
                    if sent_at > cutoff_60d_s:
                        result['total_in_repingqueue'] += 1
        except Exception:
            pass

    return result


def format_lead_followup(status: dict) -> str:
    lines = []

    pending = status.get('pending_approvals', [])
    if pending:
        lines.append(f'**{len(pending)} Lead Repl{"ies" if len(pending) != 1 else "y"} Waiting for Note Approval in Telegram**')
        for p in pending[:5]:
            name     = p.get('contact_name') or 'Unknown'
            interest = (p.get('interest_level') or 'unknown').upper()
            step     = p.get('next_step') or ''
            emoji    = {'HOT': '🔥', 'WARM': '🟡', 'COLD': '❄️'}.get(interest, '⚪')
            lines.append(f'  {emoji} {name} — {interest}  |  Next: {step}')
        if len(pending) > 5:
            lines.append(f'  ...and {len(pending) - 5} more in Telegram')
    else:
        lines.append('**No pending note approvals** — inbox clear')

    recent = status.get('texted_recently', [])
    if recent:
        lines.append(f'\n**Texted in Last 7 Days:** {len(recent)} lead{"s" if len(recent) != 1 else ""}')
        for r in recent[:5]:
            name     = r.get('contact_name') or r.get('contact_id', '')
            sent     = (r.get('sent_at') or '')[:10]
            priority = (r.get('priority') or '').upper()
            lines.append(f'  • {name}  (sent {sent}, {priority} priority)')

    in_queue = status.get('total_in_repingqueue', 0)
    if in_queue:
        lines.append(f'**Re-Ping Queue (60-day cycle):** {in_queue} lead{"s" if in_queue != 1 else ""} being tracked')

    if not any([pending, recent, in_queue]):
        lines.append('Lead follow-up system active — no recent activity to report')

    return '\n'.join(lines)


# ── Ratio helpers ─────────────────────────────────────────────────────────────
def ratio(num: int, den: int) -> str:
    if num == 0 or den == 0:
        return 'N/A'
    return f'1 in {round(den / num)}'


def pct(num: int, den: int) -> str:
    if den == 0:
        return 'N/A'
    return f'{round(num / den * 100)}%'


def vs(actual: int, target: int) -> str:
    if target == 0:
        return str(actual)
    remaining = target - actual
    symbol = '✓' if actual >= target else f'{remaining} to go'
    return f'{actual} / {target}  [{symbol}]'


# ── Format sections ───────────────────────────────────────────────────────────
def format_pipeline(pipelines: dict, closed: dict) -> str:
    lines = []

    lines.append(f'**Closed Deals**')
    lines.append(f'  MTD: {closed["mtd_count"]} deals | ${closed["mtd_value"]:,.0f} commission')
    lines.append(f'  YTD: {closed["ytd_count"]} deals | ${closed["ytd_value"]:,.0f} commission')

    if not pipelines:
        lines.append('\nNo open opportunities found in GHL.')
        return '\n'.join(lines)

    lines.append('')
    for pipeline, stages in pipelines.items():
        total_count = sum(s['count'] for s in stages.values())
        total_value = sum(s['value'] for s in stages.values())
        lines.append(f'**{pipeline}** — {total_count} open | ${total_value:,.0f} total value')
        for stage, data in stages.items():
            val = f'${data["value"]:,.0f}'
            lines.append(f'  • {stage}: {data["count"]} ({val})')
    return '\n'.join(lines)


def format_kpis(yesterday: Optional[dict], mtd: dict) -> str:
    lines = []
    if yesterday:
        lines.append(f'**Yesterday ({YESTERDAY})**')
        lines.append(f'  Contacts: {yesterday.get("contacts", 0)} | Leads: {yesterday.get("leads", 0)} | Emails: {yesterday.get("emails", 0)}')
        lines.append(f'  Seller Appts Set: {yesterday.get("appts_set", 0)} | Met: {yesterday.get("appts_met", 0)}')
        lines.append(f'  Listings: {yesterday.get("listings", 0)} | Closings: {yesterday.get("closings", 0)}')
        lines.append(f'  Buyer Appts Set: {yesterday.get("buyer_appts_set", 0)} | Met: {yesterday.get("buyer_appts_met", 0)} | Contracts: {yesterday.get("buyer_contracts_signed", 0)}')
        lines.append(f'  Agent Contacts: {yesterday.get("agent_contacts", 0)} | Discoveries Set: {yesterday.get("agent_discoveries_set", 0)} | Met: {yesterday.get("agent_discoveries_met", 0)}')
        lines.append(f'  3-Ways Set: {yesterday.get("agent_3ways_set", 0)} | Met: {yesterday.get("agent_3ways_met", 0)} | Verbals: {yesterday.get("agent_verbals", 0)} | Onboarded: {yesterday.get("agent_onboarded", 0)}')
        if yesterday.get('notes'):
            lines.append(f'  Notes: {yesterday["notes"]}')
    else:
        lines.append(f'**Yesterday ({YESTERDAY})** — no entry logged')

    lines.append(f'\n**MTD ({FIRST_OF_MONTH.strftime("%b %Y")})**')
    lines.append(f'  Seller — Contacts: {mtd["contacts"]} | Appts Set: {mtd["appts_set"]} | Met: {mtd["appts_met"]} | Listings: {mtd["listings"] + mtd["listings_other"]} | Closings: {mtd["closings"]}')
    lines.append(f'  Buyer  — Appts Set: {mtd["buyer_appts_set"]} | Met: {mtd["buyer_appts_met"]} | Contracts: {mtd["buyer_contracts_signed"]}')
    lines.append(f'  Agent  — Contacts: {mtd["agent_contacts"]} | Discoveries Set: {mtd["agent_discoveries_set"]} | Met: {mtd["agent_discoveries_met"]} | 3-Ways: {mtd["agent_3ways_set"]}/{mtd["agent_3ways_met"]} | Verbals: {mtd["agent_verbals"]} | Onboarded: {mtd["agent_onboarded"]}')

    lines.append(f'\n**Key Ratios (MTD)**')
    lines.append(f'  Contacts → Appt Set:  {ratio(mtd["contacts"], mtd["appts_set"])} (target: 1 in 25)')
    lines.append(f'  Appt Set → Listing:   {ratio(mtd["appts_set"], mtd["listings"])} (target: 1 in 5)')
    lines.append(f'  Appt Met → Listing:   {ratio(mtd["appts_met"], mtd["listings"])} (target: 1 in 2)')
    lines.append(f'  Appt Met Rate:        {pct(mtd["appts_met"], mtd["appts_set"])}')
    lines.append(f'  Contacts/Day:         {round(mtd["contacts"] / max(TODAY.day - 1, 1), 1)}')
    return '\n'.join(lines)


def format_weekly_progress(wtd: dict, targets: Optional[dict]) -> str:
    lines = [f'**Week of {WEEK_START.strftime("%b %d")} — Day {TODAY.weekday() + 1}/5**']

    if not targets:
        lines.append('  No weekly targets set — run `/week` to generate them.')
        lines.append(f'\n  WTD: Seller contacts {wtd["contacts"]} | Appts set {wtd["appts_set"]} | Agent contacts {wtd["agent_contacts"]} | Discoveries {wtd["agent_discoveries_set"]}')
        return '\n'.join(lines)

    s = targets.get('seller', {})
    b = targets.get('buyer', {})
    a = targets.get('agent', {})

    if targets.get('focus_note'):
        lines.append(f'  Focus: {targets["focus_note"]}')

    lines.append('\n**SELLER** (WTD vs target)')
    lines.append(f'  Contacts:    {vs(wtd["contacts"], s.get("contacts", 0))}')
    lines.append(f'  Appts Set:   {vs(wtd["appts_set"], s.get("appts_set", 0))}')
    lines.append(f'  Appts Met:   {vs(wtd["appts_met"], s.get("appts_met", 0))}')
    lines.append(f'  Listings:    {vs(wtd["listings"], s.get("listings", 0))}')
    lines.append(f'  Closings:    {vs(wtd["closings"], s.get("closings", 0))}')

    lines.append('\n**BUYER** (WTD vs target)')
    lines.append(f'  Appts Set:   {vs(wtd["buyer_appts_set"], b.get("appts_set", 0))}')
    lines.append(f'  Appts Met:   {vs(wtd["buyer_appts_met"], b.get("appts_met", 0))}')
    lines.append(f'  Contracts:   {vs(wtd["buyer_contracts_signed"], b.get("contracts_signed", 0))}')

    lines.append('\n**AGENT RECRUITING** (WTD vs target)')
    lines.append(f'  Contacts:        {vs(wtd["agent_contacts"], a.get("contacts", 0))}')
    lines.append(f'  Discoveries Set: {vs(wtd["agent_discoveries_set"], a.get("discoveries_set", 0))}')
    lines.append(f'  Discoveries Met: {vs(wtd["agent_discoveries_met"], a.get("discoveries_met", 0))}')
    lines.append(f'  3-Ways Set:      {vs(wtd["agent_3ways_set"], a.get("3ways_set", 0))}')
    lines.append(f'  3-Ways Met:      {vs(wtd["agent_3ways_met"], a.get("3ways_met", 0))}')
    lines.append(f'  Verbals:         {vs(wtd["agent_verbals"], a.get("verbals", 0))}')
    lines.append(f'  Onboarded:       {vs(wtd["agent_onboarded"], a.get("onboarded", 0))}')

    c = targets.get('content', {})
    lines.append('\n**CONTENT** (WTD vs target)')
    lines.append(f'  Stories:         {vs(wtd.get("stories_posted", 0), c.get("stories", 5))}')
    lines.append(f'  Posts/Reels:     {vs(wtd.get("posts_reels_posted", 0), c.get("posts_reels", 5))}')
    lines.append(f'  YouTube:         {vs(wtd.get("youtube_posted", 0), c.get("youtube", 1))}')

    return '\n'.join(lines)


def format_calendar(today_events: list, upcoming: list) -> str:
    def fmt_time(iso: str) -> str:
        try:
            dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
            local = dt.astimezone()
            return local.strftime('%-I:%M%p').lower()
        except Exception:
            return iso[:10]

    lines = []
    if today_events:
        lines.append(f'**Today ({TODAY.strftime("%a %b %d")})**')
        for e in today_events:
            if e.get('all_day'):
                time_str = 'all day'
            else:
                start = fmt_time(e.get('start_time', ''))
                end = fmt_time(e.get('end_time', ''))
                time_str = f'{start}–{end}'
            loc = f' @ {e["location"]}' if e.get('location') else ''
            lines.append(f'  {time_str}  {e["title"]}{loc}')
    else:
        lines.append(f'**Today ({TODAY.strftime("%a %b %d")})** — no events')

    if upcoming:
        lines.append(f'\n**Next 3 Days**')
        for e in upcoming:
            day = e.get('start_time', '')[:10]
            try:
                day = datetime.fromisoformat(day).strftime('%a %b %d')
            except Exception:
                pass
            lines.append(f'  {day}  {e["title"]}')

    return '\n'.join(lines)


def format_content(mtd: dict, wtd: dict) -> str:
    daily_target_stories = 1
    daily_target_posts   = 1
    days_elapsed = max(TODAY.day - 1, 1)
    work_days_elapsed = max(TODAY.weekday(), 1)

    mtd_stories = mtd.get('stories_posted', 0)
    mtd_posts   = mtd.get('posts_reels_posted', 0)
    mtd_yt      = mtd.get('youtube_posted', 0)
    wtd_stories = wtd.get('stories_posted', 0)
    wtd_posts   = wtd.get('posts_reels_posted', 0)
    wtd_yt      = wtd.get('youtube_posted', 0)

    mtd_story_target = days_elapsed * daily_target_stories
    mtd_post_target  = days_elapsed * daily_target_posts

    def gap(actual, target):
        diff = target - actual
        if diff <= 0:
            return f'{actual} ✓'
        return f'{actual} ({diff} behind)'

    lines = [
        f'**MTD Content ({FIRST_OF_MONTH.strftime("%b %Y")})**',
        f'  Stories:     {gap(mtd_stories, mtd_story_target)}  (target: 1/day)',
        f'  Posts/Reels: {gap(mtd_posts, mtd_post_target)}  (target: 1/day)',
        f'  YouTube:     {mtd_yt} posted',
        f'\n**WTD Content (this week)**',
        f'  Stories:     {wtd_stories}',
        f'  Posts/Reels: {wtd_posts}',
        f'  YouTube:     {wtd_yt}',
    ]
    return '\n'.join(lines)


def format_hot_sellers(sellers: list) -> str:
    if not sellers:
        return 'No hot sellers found. Tag contacts `hot-30` in GHL or move them to Apt Set / Attended Not Signed.'

    stage_order = {
        'Apt Attended - Not Signed': 0,
        'Apt Attended-Not Signed': 0,
        'Listing Taken': 1,
        'Apt Set': 2,
        'hot-30 tag': 3,
    }
    sellers_sorted = sorted(sellers, key=lambda x: stage_order.get(x['stage'], 9))

    lines = []
    for s in sellers_sorted:
        val = f' | ${s["value"]:,.0f}' if s['value'] > 0 else ''
        activity = f' | last activity: {s["last_activity"]}' if s['last_activity'] else ''
        flag = ' ⚠️ no value set' if s['value'] == 0 and s['source'] == 'stage' else ''
        lines.append(f'  • **{s["name"]}** — {s["stage"]}{val}{activity}{flag}')

    return '\n'.join(lines)


def format_bclub(session: Optional[dict]) -> str:
    if not session:
        return 'No Breakfast Club sessions in database yet.'
    takeaways = session.get('key_takeaways') or []
    top = takeaways[:3] if isinstance(takeaways, list) else []
    lines = [f'**{session["title"]}** ({session["session_date"]})']
    if session.get('summary'):
        lines.append(session['summary'])
    if top:
        lines.append('Top takeaways:')
        for t in top:
            lines.append(f'  • {t}')
    return '\n'.join(lines)


# ── Generate brief with Claude ────────────────────────────────────────────────
def generate_brief(pipeline_text: str, kpi_text: str, weekly_text: str, bclub_text: str,
                   calendar_text: str = '', content_text: str = '',
                   hot_sellers_text: str = '', section7_fragment: str = '',
                   lead_followup_text: str = '') -> str:
    system = """You are the AI OS for Ashley Diep, a real estate agent and entrepreneur in Houston.

Ashley runs three businesses:
- PROAGENT (real estate sales — sellers and buyers, 3% commission, target 2-3 closings/month)
- COLLAB (agent recruitment into her brokerage, target 50 agents by end of 2026, currently at 16)
- High Key Solutions (AI systems for real estate agents — pre-revenue)

Daily schedule (Mon–Thu): 7:30am ISA roleplay (30 min) | 8:00–11:00am seller cold calling | 11:00am Co-Lab call | 11:30–11:50am daily call review (Ashley + Josh) | 12:00–1:00pm agent recruiting calls
Friday additions: 11:30am ISA 1:1 with Josh | 1:00–3:00pm content creation | 3:00–4:00pm weekly review
Saturday: 10:00am–12:00pm batch content recording | 1:00–2:00pm strategy/brainstorm
Ashley also has an ISA (Josh) — his numbers are tracked separately in isa_daily_kpis. Flag if Josh's appts are behind target (1/day minimum).
Target: 2 seller appts/day set | ~25 contacts per appt | relationship-based agent recruiting

Content goals (critical for brand and lead gen):
- Instagram/Facebook: 1 story/day + 1 post or reel/day (every single day)
- YouTube: consistent posting to feed home evaluation funnel
- Content feeds seller and buyer leads, agent recruitment visibility, and High Key Solutions brand
- If content is behind, flag it — missed posting days compound fast

Write in a direct, no-fluff tone. Ashley is data-driven. Reference actual numbers in recommendations."""

    friday_note = ""
    if TODAY.weekday() == 4:  # Friday
        friday_note = "\n\nIMPORTANT: Today is Friday. Fixed blocks: 11:30am ISA 1:1 with Josh (KPI review + call recording review + one skill drill), 1:00–3:00pm content creation and post scheduling, 3:00–4:00pm weekly review and planning for next week."
    saturday_note = ""
    if TODAY.weekday() == 5:  # Saturday
        saturday_note = "\n\nIMPORTANT: Today is Saturday. Fixed blocks: 10:00am–12:00pm batch content recording (film 4–6 pieces), 12:00–1:00pm edit and schedule posts, 1:00–2:00pm strategy and brainstorm session."

    user = f"""Generate Ashley's Daily Brief for {TODAY.strftime('%A, %B %d, %Y')}.{friday_note}{saturday_note}

# Daily Brief — {TODAY.strftime('%A, %B %d, %Y')}

## 1. Sales Pipeline (GHL)
{pipeline_text}

## 2. Yesterday's Numbers & MTD
{kpi_text}

## 3. Weekly Progress
{weekly_text}

## 4. Today's Calendar & Schedule
{calendar_text}

Build a time-blocked schedule for today that incorporates the above calendar events AND Ashley's fixed routine:
- 7:30am: ISA roleplay with Josh (30 min — note what to drill based on yesterday's numbers)
- 8:00–11:00am: seller cold calling (note what lists to hit)
- 11:00am: Co-Lab call
- 11:30–11:50am: daily call review (pull 1 of Ashley's calls + 1 of Josh's)
- 12:00–1:00pm: agent recruiting calls
- Any calendar events: slot them in and flag conflicts with the above blocks
Keep it tight — one line per block.

## 5. Latest Breakfast Club
{bclub_text}

## 6. Hot Seller Radar
{hot_sellers_text}

For each person: note how long since last contact, what their next step should be, and flag anyone overdue for a follow-up (no activity in 7+ days). Keep it tight — one action per person.

## 7. Lead Follow-Up AI
{lead_followup_text}

If there are pending Telegram note approvals — flag it as the first thing to do before calling. If any replied lead is marked HOT, call them today. Note how many leads are in the 60-day re-ping queue.

## 8. Content & Brand
{content_text}

Flag if stories or posts are behind the daily target. Suggest what type of content to post today based on Ashley's priorities (seller leads, agent recruiting, High Key Solutions brand).

## 9. Today's Top 3 Priorities
3 specific, actionable priorities for today. Reference actual numbers. If something is behind target — including content — name it and say what to do about it.{section7_fragment}"""

    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': ANTHROPIC_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        json={
            'model': 'claude-opus-4-7',
            'max_tokens': 2500,
            'system': system,
            'messages': [{'role': 'user', 'content': user}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


# ── Main ───────────────────────────────────────────────────────────────────────
def sync_calendar_now():
    try:
        import subprocess
        sync_script = Path(__file__).parent / 'sync' / 'google_calendar.py'
        result = subprocess.run(
            [sys.executable, str(sync_script)],
            capture_output=True, text=True, timeout=30,
        )
        last_line = [l for l in result.stdout.strip().splitlines() if l.strip()]
        print(f'  Calendar sync: {last_line[-1] if last_line else "done"}')
    except Exception as e:
        print(f'  Calendar sync skipped: {e}')


def run_morning():
    print(f'\nGenerating Daily Brief for {TODAY}...')

    print('  Syncing Google Calendar...')
    sync_calendar_now()

    print('  Pulling GHL pipeline...')
    pipelines = get_pipeline()
    closed_deals = get_closed_deals()
    hot_sellers = get_hot_sellers()

    print('  Pulling KPIs...')
    yesterday_kpis = get_yesterday_kpis()
    mtd_kpis       = get_mtd_kpis()
    wtd_kpis       = get_wtd_kpis()

    print('  Pulling weekly targets...')
    weekly_targets = get_weekly_targets()
    if not weekly_targets:
        print('  (No weekly targets found — run /week to set them)')

    print('  Pulling latest Breakfast Club session...')
    bclub = get_latest_bclub()

    print('  Pulling lead follow-up status...')
    lead_followup_status = get_lead_followup_status()

    print('  Pulling calendar...')
    today_events = get_todays_events()
    upcoming_events = get_upcoming_events(days=3)

    # Decision Engine pre-brief
    pre_brief = None
    section7_fragment = ''
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scripts.decisions.brief_integration import (
            run_pre_brief, build_section7_prompt_fragment, post_process_brief,
            render_section7_gated, render_reviews_due_block, render_revisit_block,
            mark_revisits_surfaced, render_section8,
        )
        print('  Running Decision Engine pre-brief...')
        pre_brief = run_pre_brief()
        if pre_brief.expired_now:
            print(f'  (Expired {pre_brief.expired_now} stale pending rec(s))')
        section7_fragment = build_section7_prompt_fragment(pre_brief)
    except Exception as e:
        print(f'  Decision Engine pre-brief skipped: {e}')

    print('  Generating brief with Claude Opus...')
    pipeline_text      = format_pipeline(pipelines, closed_deals)
    kpi_text           = format_kpis(yesterday_kpis, mtd_kpis)
    weekly_text        = format_weekly_progress(wtd_kpis, weekly_targets)
    bclub_text         = format_bclub(bclub)
    calendar_text      = format_calendar(today_events, upcoming_events)
    content_text       = format_content(mtd_kpis, wtd_kpis)
    hot_sellers_text   = format_hot_sellers(hot_sellers)
    lead_followup_text = format_lead_followup(lead_followup_status)

    brief = generate_brief(pipeline_text, kpi_text, weekly_text, bclub_text, calendar_text, content_text, hot_sellers_text, section7_fragment, lead_followup_text)

    # Decision Engine post-process
    if pre_brief is not None:
        try:
            if not pre_brief.gate_active:
                result = post_process_brief(brief)
                brief = result['brief']
                if result['emitted']:
                    print(f'  Decision Engine: emitted {len(result["emitted"])} rec(s)')
                if result['suppressed']:
                    print(f'  Decision Engine: suppressed {len(result["suppressed"])} rec(s)')
            else:
                brief += '\n' + render_section7_gated(pre_brief)

            reviews_block = render_reviews_due_block(pre_brief)
            revisits_block = render_revisit_block(pre_brief)
            if reviews_block:
                brief += '\n' + reviews_block
            if revisits_block:
                brief += '\n' + revisits_block
            if pre_brief.revisits_due:
                mark_revisits_surfaced(pre_brief)

            from datetime import datetime
            section8 = render_section8(datetime.combine(TODAY, datetime.min.time()))
            if section8:
                brief += '\n' + section8
        except Exception as e:
            print(f'  Decision Engine post-process skipped: {e}')

    out_path = OUTPUTS_DIR / f'{TODAY}.md'
    out_path.write_text(brief)
    print(f'\n  Saved to: outputs/briefs/{TODAY}.md\n')
    print('─' * 60)
    print(brief)
    print('─' * 60)


def run_evening():
    print(f'\nGenerating Evening Recap for {TODAY}...')
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scripts.decisions.brief_integration import build_evening_recap
        recap = build_evening_recap()
    except Exception as e:
        recap = f'Evening recap unavailable: {e}'

    out_path = OUTPUTS_DIR / f'{TODAY}-evening.md'
    out_path.write_text(recap)
    print(f'\n  Saved to: outputs/briefs/{TODAY}-evening.md\n')
    print('─' * 60)
    print(recap)
    print('─' * 60)


def main():
    if MODE == 'evening':
        run_evening()
    else:
        run_morning()


if __name__ == '__main__':
    main()
