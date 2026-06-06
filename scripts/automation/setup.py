#!/usr/bin/env python3
"""
Agent Attraction — Setup Wizard
Run this once per agent to generate their config.json and register them in the system.

Usage:
  python3 setup.py              # interactive wizard
  python3 setup.py --agent-id ashley_diep  # pre-fill agent ID
"""
import json
import os
import re
import sys
import argparse
import secrets
from pathlib import Path

try:
    import requests
except ImportError:
    print('ERROR: requests not installed. Run: pip3 install requests')
    sys.exit(1)

CENTRAL_SUPABASE_URL = 'https://aiwdgrrxfddaxfyahisc.supabase.co'
CENTRAL_SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFpd2RncnJ4ZmRkYXhmeWFoaXNjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzA2NTkxMCwiZXhwIjoyMDkyNjQxOTEwfQ.Doyra7FnSUxi1fYQNG99loeJZau_boYuVAr9_y4Ukp0'
WEBHOOK_BASE = 'https://proagent-telegram.ashleydiepnm.workers.dev'

SB_HEADERS = {
    'apikey': CENTRAL_SUPABASE_KEY,
    'Authorization': f'Bearer {CENTRAL_SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates,return=minimal',
}


def ask(prompt: str, default: str = '', required: bool = True) -> str:
    suffix = f' [{default}]' if default else ''
    while True:
        val = input(f'{prompt}{suffix}: ').strip()
        if not val and default:
            return default
        if val:
            return val
        if not required:
            return ''
        print('  (required)')


def ask_list(prompt: str, default: list = None) -> list:
    default_str = ', '.join(default) if default else ''
    suffix = f' [{default_str}]' if default_str else ''
    val = input(f'{prompt}{suffix}: ').strip()
    if not val and default:
        return default
    return [v.strip() for v in val.split(',') if v.strip()]


def ask_int(prompt: str, default: int) -> int:
    val = input(f'{prompt} [{default}]: ').strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def make_agent_id(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower().strip()).strip('_')


def test_ghl(api_key: str, location_id: str) -> bool:
    try:
        resp = requests.get(
            'https://rest.gohighlevel.com/v1/contacts/?limit=1',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def test_anthropic(api_key: str) -> bool:
    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
            json={'model': 'claude-haiku-4-5-20251001', 'max_tokens': 10, 'messages': [{'role': 'user', 'content': 'hi'}]},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def test_groq(api_key: str) -> bool:
    try:
        resp = requests.get(
            'https://api.groq.com/openai/v1/models',
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def register_agent(config: dict):
    """Write agent config to central Supabase agents table so the Worker can look it up."""
    row = {
        'agent_id': config['agent_id'],
        'agent_name': config['agent_name'],
        'recruiter_names': config['recruiter_names'],
        'my_emails': config['my_emails'],
        'internal_emails': config['internal_emails'],
        'ghl_api_key': config['ghl_api_key'],
        'ghl_location_id': config['ghl_location_id'],
        'ghl_tags': config['ghl_tags'],
        'notification_telegram_chat_id': config.get('notification_telegram_chat_id'),
        'notification_email': config.get('notification_email'),
        'reengage_threshold_days': config.get('reengage_threshold_days', 60),
    }
    resp = requests.post(
        f'{CENTRAL_SUPABASE_URL}/rest/v1/agents',
        headers=SB_HEADERS,
        json=row,
        timeout=15,
    )
    resp.raise_for_status()


def run_calendar_auth(config: dict):
    """Run Google Calendar OAuth for this agent."""
    print('\n  Opening browser for Google Calendar authorization...')
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        oauth_keys = Path(__file__).parents[2] / 'gcp-oauth.keys.json'
        token_file = Path(__file__).parents[2] / f'data/tokens/calendar_token_{config["agent_id"]}.json'
        token_file.parent.mkdir(parents=True, exist_ok=True)

        scopes = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), scopes)
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(str(oauth_keys), scopes)
            creds = flow.run_local_server(port=0)
            token_file.write_text(creds.to_json())

        config['calendar_token_file'] = str(token_file)
        print(f'  Calendar authorized. Token saved to: {token_file.name}')
        return True
    except Exception as e:
        print(f'  Warning: Calendar auth failed — {e}')
        print('  You can run calendar_to_ghl.py later and it will prompt for auth.')
        return False


def main():
    parser = argparse.ArgumentParser(description='Agent Attraction setup wizard')
    parser.add_argument('--agent-id', help='Pre-fill agent ID')
    parser.add_argument('--output', default='config.json', help='Output config file path')
    args = parser.parse_args()

    print('\n' + '=' * 60)
    print('  Agent Attraction — Setup Wizard')
    print('  Sets up your calendar → GHL + AI transcriber system')
    print('=' * 60 + '\n')

    # ── Agent identity ────────────────────────────────────────────────────────

    agent_name = ask('Your full name')
    suggested_id = args.agent_id or make_agent_id(agent_name)
    agent_id = ask('Agent ID (no spaces, used in your webhook URL)', default=suggested_id)
    agent_id = make_agent_id(agent_id)

    print(f'\n  Your Fireflies webhook URL will be:')
    print(f'  {WEBHOOK_BASE}/fireflies/{agent_id}\n')

    # ── Recruiter names ───────────────────────────────────────────────────────

    print('Recruiter names (the people whose Calendly calls we watch):')
    recruiter_names = ask_list(
        '  Names (comma-separated)',
        default=['Michelle Wilson', 'Chad Cooley'],
    )

    # ── Emails ────────────────────────────────────────────────────────────────

    print('\nYour email addresses (we skip creating contacts for these):')
    my_emails = ask_list('  Your emails (comma-separated)')

    print('\nOther internal team emails to skip (optional):')
    internal_emails = ask_list('  Internal emails', default=[])

    # ── GHL ───────────────────────────────────────────────────────────────────

    print('\nGoHighLevel credentials:')
    print('  Find these at: Settings → Integrations → API Key in your GHL account')
    ghl_api_key = ask('  GHL API Key')
    ghl_location_id = ask('  GHL Location ID')

    print('  Testing GHL connection...', end=' ', flush=True)
    if test_ghl(ghl_api_key, ghl_location_id):
        print('✓')
    else:
        print('✗ — could not connect. Check your key and try again.')
        if ask('Continue anyway? (yes/no)', default='no') != 'yes':
            sys.exit(1)

    print('\nGHL tags to apply to new contacts:')
    ghl_tags = ask_list('  Tags', default=['agent', 'agentnewsletter'])

    # ── Notifications ─────────────────────────────────────────────────────────

    print('\nNotifications — where to send meeting summaries:')
    notification_email = ask('  Your email for summaries', default=my_emails[0] if my_emails else '')
    telegram_chat_id_str = ask('  Telegram chat ID (leave blank to skip)', required=False)
    notification_telegram_chat_id = int(telegram_chat_id_str) if telegram_chat_id_str.isdigit() else None

    # ── API keys ──────────────────────────────────────────────────────────────

    print('\nAPI keys:')
    anthropic_key = ask('  Anthropic API key (claude.ai/settings → API keys)')
    print('  Testing Anthropic...', end=' ', flush=True)
    print('✓' if test_anthropic(anthropic_key) else '✗ (check key)')

    groq_key = ask('  Groq API key for transcription (console.groq.com — free)')
    print('  Testing Groq...', end=' ', flush=True)
    print('✓' if test_groq(groq_key) else '✗ (check key)')

    # ── Re-engagement ─────────────────────────────────────────────────────────

    print('\nRe-engagement:')
    reengage_days = ask_int('  Days without contact before flagging as cold', default=60)

    # ── Build config ──────────────────────────────────────────────────────────

    config = {
        'agent_id': agent_id,
        'agent_name': agent_name,
        'recruiter_names': recruiter_names,
        'my_emails': my_emails,
        'internal_emails': internal_emails,
        'ghl_api_key': ghl_api_key,
        'ghl_location_id': ghl_location_id,
        'ghl_tags': ghl_tags,
        'notification_email': notification_email,
        'notification_telegram_chat_id': notification_telegram_chat_id,
        'reengage_threshold_days': reengage_days,
        'anthropic_api_key': anthropic_key,
        'groq_api_key': groq_key,
        'supabase_url': CENTRAL_SUPABASE_URL,
        'supabase_service_role_key': CENTRAL_SUPABASE_KEY,
    }

    # ── Google Calendar auth ──────────────────────────────────────────────────

    print('\nGoogle Calendar authorization:')
    do_auth = ask('  Authorize Google Calendar now? (yes/no)', default='yes')
    if do_auth.lower() == 'yes':
        run_calendar_auth(config)

    # ── Save config ───────────────────────────────────────────────────────────

    output_path = Path(__file__).parent / args.output
    output_path.write_text(json.dumps(config, indent=2))
    print(f'\n  Config saved to: {output_path}')

    # ── Register in central Supabase ──────────────────────────────────────────

    print('  Registering agent in central system...', end=' ', flush=True)
    try:
        register_agent(config)
        print('✓')
    except Exception as e:
        print(f'✗ — {e}')
        print('  (You can still use the scripts locally, but the Fireflies webhook won\'t work yet.)')

    # ── Done ──────────────────────────────────────────────────────────────────

    print('\n' + '=' * 60)
    print('  Setup complete!')
    print('=' * 60)
    print(f"""
Next steps:

1. ADD FIREFLIES WEBHOOK
   URL: {WEBHOOK_BASE}/fireflies/{agent_id}
   Trigger: "Transcription completed"
   → Settings → Integrations → Webhooks in Fireflies.ai

2. RUN THE CALENDAR SCANNER
   python3 scripts/automation/calendar_to_ghl.py
   (add --dry-run first to preview)

3. SCHEDULE IT (optional)
   Add to cron or your daily /sync routine to run automatically.

4. TEST THE TRANSCRIBER
   Drop a recording in ~/meeting-recordings/inbox/
   python3 scripts/automation/meeting_transcriber.py ~/meeting-recordings/inbox/test.mp4

5. RE-ENGAGEMENT
   python3 scripts/automation/reengage.py --dry-run
""")


if __name__ == '__main__':
    main()
