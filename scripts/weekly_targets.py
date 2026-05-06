#!/usr/bin/env python3
"""
Weekly Targets Generator — Ashley Diep / ProAgent AI OS
Looks at year-end goals, current trajectory, and last week's numbers,
then uses Claude to generate specific weekly targets.
Saves to data/weekly-targets/YYYY-Www.json for the daily brief to read.
"""

import os
import json
import sys
import requests
from datetime import date, timedelta
from pathlib import Path

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

SB_HEADERS = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}

TARGETS_DIR = Path(__file__).parents[1] / 'data' / 'weekly-targets'
TARGETS_DIR.mkdir(parents=True, exist_ok=True)

TODAY       = date.today()
WEEK_START  = TODAY - timedelta(days=TODAY.weekday())
WEEK_END    = WEEK_START + timedelta(days=4)
WEEK_KEY    = TODAY.strftime('%Y-W%V')
LAST_WEEK_START = WEEK_START - timedelta(days=7)
FIRST_OF_YEAR   = TODAY.replace(month=1, day=1)

SELLER_FIELDS = ['contacts', 'leads', 'appts_set', 'appts_met', 'listings', 'closings']
BUYER_FIELDS  = ['buyer_appts_set', 'buyer_appts_met', 'buyer_contracts_signed']
AGENT_FIELDS  = ['agent_contacts', 'agent_discoveries_set', 'agent_discoveries_met',
                 'agent_3ways_set', 'agent_3ways_met', 'agent_verbals', 'agent_onboarded']
ALL_FIELDS    = SELLER_FIELDS + BUYER_FIELDS + AGENT_FIELDS


# ── Supabase helpers ──────────────────────────────────────────────────────────
def sb_get(table: str, params: dict) -> list:
    resp = requests.get(
        f'{SUPABASE_URL}/rest/v1/{table}',
        headers={**SB_HEADERS, 'Prefer': 'count=none'},
        params=params, timeout=15,
    )
    return resp.json() if resp.status_code in (200, 206) else []


def sum_rows(rows: list, fields: list) -> dict:
    totals = {f: 0 for f in fields}
    for r in rows:
        for f in fields:
            totals[f] += r.get(f) or 0
    return totals


def get_ytd() -> dict:
    rows = sb_get('daily_kpis', {'date': f'gte.{FIRST_OF_YEAR}', 'select': ','.join(ALL_FIELDS)})
    return sum_rows(rows, ALL_FIELDS)


def get_last_week() -> dict:
    rows = sb_get('daily_kpis', {
        'date': f'gte.{LAST_WEEK_START}',
        'date': f'lte.{WEEK_START - timedelta(days=1)}',
        'select': ','.join(ALL_FIELDS),
    })
    return sum_rows(rows, ALL_FIELDS)


def get_agent_pipeline() -> dict:
    rows = sb_get('ghl_opportunities', {
        'pipeline_name': 'eq.Agent Pipeline',
        'status': 'eq.open',
        'select': 'stage_name',
    })
    stages = {}
    for r in rows:
        s = r.get('stage_name', 'Unknown')
        stages[s] = stages.get(s, 0) + 1
    return stages


# ── Claude call ───────────────────────────────────────────────────────────────
def claude(messages: list, max_tokens: int = 800) -> str:
    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={'x-api-key': ANTHROPIC_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
        json={'model': 'claude-sonnet-4-6', 'max_tokens': max_tokens, 'messages': messages},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def generate_targets(ytd: dict, last_week: dict, agent_pipeline: dict) -> dict:
    months_remaining = 12 - TODAY.month + 1 - (TODAY.day / 30)

    prompt = f"""Generate weekly KPI targets for Ashley Diep, a Houston real estate agent and recruiter.

TODAY: {TODAY} | WEEK: {WEEK_START} to {WEEK_END}

YEAR-END GOALS:
- Seller: 2–3 closings/month
- Agent recruitment: reach 50 agents by Dec 31 (currently 16, need {34} more in ~{round(months_remaining, 1)} months = {round(34 / max(months_remaining, 0.1), 1)}/month)

YTD ACTUALS:
Seller — contacts: {ytd['contacts']}, appts set: {ytd['appts_set']}, appts met: {ytd['appts_met']}, listings: {ytd['listings']}, closings: {ytd['closings']}
Buyer  — appts set: {ytd['buyer_appts_set']}, met: {ytd['buyer_appts_met']}, contracts: {ytd['buyer_contracts_signed']}
Agent  — contacts: {ytd['agent_contacts']}, discoveries set: {ytd['agent_discoveries_set']}, met: {ytd['agent_discoveries_met']}, 3-ways set: {ytd['agent_3ways_set']}, met: {ytd['agent_3ways_met']}, verbals: {ytd['agent_verbals']}, onboarded: {ytd['agent_onboarded']}

LAST WEEK:
Seller — contacts: {last_week['contacts']}, appts set: {last_week['appts_set']}, met: {last_week['appts_met']}
Agent  — contacts: {last_week['agent_contacts']}, discoveries set: {last_week['agent_discoveries_set']}, met: {last_week['agent_discoveries_met']}, verbals: {last_week['agent_verbals']}, onboarded: {last_week['agent_onboarded']}

AGENT PIPELINE (GHL): {json.dumps(agent_pipeline)}

Daily schedule: 8–11am seller calls | 11:30am–12pm agent calls | ~25 seller contacts per appt set | relationship-based agent recruiting

Return ONLY valid JSON:
{{
  "week": "{WEEK_KEY}",
  "week_start": "{WEEK_START}",
  "week_end": "{WEEK_END}",
  "generated_on": "{TODAY}",
  "seller": {{"contacts": 0, "appts_set": 0, "appts_met": 0, "listings": 0, "closings": 0}},
  "buyer": {{"appts_set": 0, "appts_met": 0, "contracts_signed": 0}},
  "agent": {{"contacts": 0, "discoveries_set": 0, "discoveries_met": 0, "3ways_set": 0, "3ways_met": 0, "verbals": 0, "onboarded": 0}},
  "focus_note": "<one sentence: the single most important focus this week>"
}}

Be realistic vs last week. Stretch toward goals but don't set targets that are 10x last week."""

    text = claude([{'role': 'user', 'content': prompt}])
    start, end = text.find('{'), text.rfind('}') + 1
    return json.loads(text[start:end])


def apply_tweaks(targets: dict, tweak_instruction: str) -> dict:
    prompt = f"""The user wants to adjust these weekly targets:
{json.dumps(targets, indent=2)}

Their instruction: "{tweak_instruction}"

Apply their changes and return the full updated JSON with the same structure. Only change what they asked. Return ONLY valid JSON."""

    text = claude([{'role': 'user', 'content': prompt}])
    start, end = text.find('{'), text.rfind('}') + 1
    return json.loads(text[start:end])


def format_targets(t: dict) -> str:
    lines = [
        f"\nWEEKLY TARGETS — {t['week']} ({t['week_start']} → {t['week_end']})",
        f"Focus: {t.get('focus_note', '')}",
        f"\nSELLER",
        f"  Contacts:   {t['seller']['contacts']}",
        f"  Appts Set:  {t['seller']['appts_set']}",
        f"  Appts Met:  {t['seller']['appts_met']}",
        f"  Listings:   {t['seller']['listings']}",
        f"  Closings:   {t['seller']['closings']}",
        f"\nBUYER",
        f"  Appts Set:  {t['buyer']['appts_set']}",
        f"  Appts Met:  {t['buyer']['appts_met']}",
        f"  Contracts:  {t['buyer']['contracts_signed']}",
        f"\nAGENT RECRUITING",
        f"  Contacts:        {t['agent']['contacts']}",
        f"  Discoveries Set: {t['agent']['discoveries_set']}",
        f"  Discoveries Met: {t['agent']['discoveries_met']}",
        f"  3-Ways Set:      {t['agent']['3ways_set']}",
        f"  3-Ways Met:      {t['agent']['3ways_met']}",
        f"  Verbals:         {t['agent']['verbals']}",
        f"  Onboarded:       {t['agent']['onboarded']}",
    ]
    return '\n'.join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    out_path = TARGETS_DIR / f'{WEEK_KEY}.json'
    force = '--force' in sys.argv

    if out_path.exists() and not force:
        targets = json.loads(out_path.read_text())
        print(f'\nExisting targets for {WEEK_KEY} (generated {targets.get("generated_on")}):')
        print(format_targets(targets))
        print('\nRun with --force to regenerate from scratch.')
        return targets

    print(f'\nGenerating weekly targets for {WEEK_KEY}...')
    print('  Pulling YTD actuals...')
    ytd = get_ytd()
    print('  Pulling last week...')
    last_week = get_last_week()
    print('  Pulling agent pipeline...')
    pipeline = get_agent_pipeline()
    print('  Generating with Claude...')
    targets = generate_targets(ytd, last_week, pipeline)

    print(format_targets(targets))
    print('\n' + '─' * 50)
    print('Tweak anything? Type your changes (e.g. "make agent contacts 30")')
    print('or press Enter to save as-is.')
    print('─' * 50)

    # Read tweaks from stdin if running interactively
    try:
        tweak = input('> ').strip()
        while tweak:
            print('  Applying...')
            targets = apply_tweaks(targets, tweak)
            print(format_targets(targets))
            print('─' * 50)
            print('Any other changes? Press Enter to save.')
            tweak = input('> ').strip()
    except (EOFError, KeyboardInterrupt):
        pass

    out_path.write_text(json.dumps(targets, indent=2))
    print(f'\nSaved to data/weekly-targets/{WEEK_KEY}.json')
    print('Your daily brief will now show progress vs these targets.\n')
    return targets


if __name__ == '__main__':
    main()
