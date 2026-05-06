#!/usr/bin/env python3
"""
Daily Brief — Ashley Diep / ProAgent AI OS
Pulls GHL pipeline, KPIs, Breakfast Club, and weekly targets from Supabase,
generates a morning intelligence report with Claude Opus,
and saves it to outputs/briefs/YYYY-MM-DD.md
"""

import os
import json
import requests
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

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


def get_yesterday_kpis() -> Optional[dict]:
    rows = sb_get('daily_kpis', {'date': f'eq.{YESTERDAY}', 'select': '*'})
    return rows[0] if rows else None


def get_mtd_kpis() -> dict:
    fields = (
        'contacts,leads,emails,appts_set,appts_met,'
        'fsbo_preview_set,fsbo_met,fsbo_listing,listings_other,listings,'
        'buyer_appts_set,buyer_appts_met,buyer_contracts_signed,closings,'
        'agent_contacts,agent_discoveries_set,agent_discoveries_met,'
        'agent_3ways_set,agent_3ways_met,agent_verbals,agent_onboarded'
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
        'agent_3ways_set,agent_3ways_met,agent_verbals,agent_onboarded'
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
def format_pipeline(pipelines: dict) -> str:
    if not pipelines:
        return 'No open opportunities found in GHL.'
    lines = []
    for pipeline, stages in pipelines.items():
        total_count = sum(s['count'] for s in stages.values())
        total_value = sum(s['value'] for s in stages.values())
        lines.append(f'\n**{pipeline}** — {total_count} open | ${total_value:,.0f} total value')
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
def generate_brief(pipeline_text: str, kpi_text: str, weekly_text: str, bclub_text: str) -> str:
    system = """You are the AI OS for Ashley Diep, a real estate agent and entrepreneur in Houston.

Ashley runs three businesses:
- PROAGENT (real estate sales — sellers and buyers, 3% commission, target 2-3 closings/month)
- COLLAB (agent recruitment into her brokerage, target 50 agents by end of 2026, currently at 16)
- High Key Solutions (AI systems for real estate agents — pre-revenue)

Daily schedule: 8–11am seller cold calling | 9:30–10am Breakfast Club | 11:30am–12pm agent recruiting calls
Target: 2 seller appts/day set | ~25 contacts per appt | relationship-based agent recruiting

Write in a direct, no-fluff tone. Ashley is data-driven. Reference actual numbers in recommendations."""

    user = f"""Generate Ashley's Daily Brief for {TODAY.strftime('%A, %B %d, %Y')}.

# Daily Brief — {TODAY.strftime('%A, %B %d, %Y')}

## 1. Sales Pipeline (GHL)
{pipeline_text}

## 2. Yesterday's Numbers & MTD
{kpi_text}

## 3. Weekly Progress
{weekly_text}

## 4. Today's Schedule
Write a time-blocked schedule for today based on Ashley's fixed routine and what needs the most attention this week based on the weekly progress above. Include:
- 8:00–11:00am block (seller cold calling — specify what to focus on based on pipeline)
- 9:30–10:00am (Breakfast Club — note it's during the calling block)
- 11:30am–12:00pm block (agent recruiting — specify what to prioritize based on weekly targets)
- Any afternoon priorities if there are pipeline follow-ups or closing tasks needed
Keep it tight — one line per block.

## 5. Latest Breakfast Club
{bclub_text}

## 6. Today's Top 3 Priorities
3 specific, actionable priorities for today. Reference actual numbers. If something is behind target, name it and say what to do about it."""

    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': ANTHROPIC_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        json={
            'model': 'claude-opus-4-7',
            'max_tokens': 2000,
            'system': system,
            'messages': [{'role': 'user', 'content': user}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print(f'\nGenerating Daily Brief for {TODAY}...')

    print('  Pulling GHL pipeline...')
    pipelines = get_pipeline()

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

    print('  Generating brief with Claude Opus...')
    pipeline_text = format_pipeline(pipelines)
    kpi_text      = format_kpis(yesterday_kpis, mtd_kpis)
    weekly_text   = format_weekly_progress(wtd_kpis, weekly_targets)
    bclub_text    = format_bclub(bclub)

    brief = generate_brief(pipeline_text, kpi_text, weekly_text, bclub_text)

    out_path = OUTPUTS_DIR / f'{TODAY}.md'
    out_path.write_text(brief)
    print(f'\n  Saved to: outputs/briefs/{TODAY}.md\n')
    print('─' * 60)
    print(brief)
    print('─' * 60)


if __name__ == '__main__':
    main()
