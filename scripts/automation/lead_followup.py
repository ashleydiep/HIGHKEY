#!/usr/bin/env python3
"""
Lead Follow-Up AI System

OUTBOUND: Finds open leads quiet for X days → Claude reads notes → drafts a
personalized, motivated text → sends it automatically via GHL SMS →
logs what went out to Telegram.

INBOUND: Scans GHL conversations for new replies from active leads → Claude
extracts key facts + drafts a GHL note → sends to Telegram with Approve/Skip
buttons. Note is only added to GHL after Ashley approves via Telegram.

Usage:
  python3 lead_followup.py                    # both modes (default)
  python3 lead_followup.py --mode outbound    # send texts only
  python3 lead_followup.py --mode inbound     # capture replies only
  python3 lead_followup.py --days 90           # leads quiet 90+ days (default: 180)
  python3 lead_followup.py --limit 15         # max outbound drafts per run (default: 10)
  python3 lead_followup.py --dry-run          # print everything, touch nothing
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import anthropic
from agent_config import load_config

CFG = load_config()

GHL_KEY          = CFG['ghl_api_key']
LOCATION_ID      = CFG['ghl_location_id']
SUPABASE_URL     = CFG['supabase_url']
SUPABASE_KEY     = CFG['supabase_service_role_key']
ANTHROPIC_KEY    = CFG['anthropic_api_key']
TELEGRAM_TOKEN   = CFG.get('telegram_bot_token') or os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = CFG.get('notification_telegram_chat_id', 5304294443)

GHL_BASE = 'https://rest.gohighlevel.com/v1'
GHL_HEADERS = {'Authorization': f'Bearer {GHL_KEY}', 'Content-Type': 'application/json'}
SB_HEADERS  = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
}

STATE_FILE = Path(__file__).parents[2] / 'data/sync-state/lead_followup.json'

DEAD_STAGE_KEYWORDS = frozenset({'dead', 'lost', 'not interested', 'do not contact', 'dnc', 'no longer'})

PIPELINE_CONTEXT = {
    'Agent Pipeline':      'recruiting a real estate agent to join COLLAB at eXp Realty',
    'Marketing Pipeline':  'a real estate seller or buyer lead',
    'Real Estate Pipeline':'a real estate seller or buyer lead',
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        'last_inbound_check': None,
        'processed_message_ids': [],
        'outbound_sent': {},        # contact_id → ISO timestamp of last SMS sent
    }


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def ghl_get(path: str) -> dict:
    url = path if path.startswith('http') else f'{GHL_BASE}{path}'
    res = requests.get(url, headers=GHL_HEADERS, timeout=30)
    res.raise_for_status()
    return res.json()


def ghl_post(path: str, data: dict) -> dict:
    url = f'{GHL_BASE}{path}'
    res = requests.post(url, headers=GHL_HEADERS, json=data, timeout=30)
    res.raise_for_status()
    return res.json()


def send_telegram(text: str, reply_markup: dict = None):
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json=payload,
            timeout=15,
        )
    except Exception as e:
        print(f'[telegram] Send failed: {e}')


def sb_post(table: str, data: dict):
    resp = requests.post(
        f'{SUPABASE_URL}/rest/v1/{table}',
        headers={**SB_HEADERS, 'Prefer': 'return=representation'},
        json=data,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def parse_json_from_claude(text: str) -> dict:
    start, end = text.find('{'), text.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError(f'No JSON in Claude response: {text[:200]}')
    return json.loads(text[start:end])


def is_dead_stage(stage_name: str) -> bool:
    stage = (stage_name or '').lower()
    return any(kw in stage for kw in DEAD_STAGE_KEYWORDS)


REPINGCOOLDOWN_DAYS = 60  # re-text every 2 months until lead responds


def last_sent_at(contact_id: str, state: dict):
    """Return datetime of last outbound text to this contact, or None."""
    sent_at = state.get('outbound_sent', {}).get(contact_id)
    if not sent_at:
        return None
    try:
        return datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
    except Exception:
        return None


def on_repingcooldown(contact_id: str, state: dict) -> bool:
    """Return True if we texted this contact within the last 60 days."""
    last = last_sent_at(contact_id, state)
    if not last:
        return False
    return last > datetime.now(timezone.utc) - timedelta(days=REPINGCOOLDOWN_DAYS)


def has_responded_since_last_text(contact_id: str, state: dict) -> bool:
    """
    Return True if the lead sent an inbound message AFTER our last outbound text.
    Uses the processed_message_ids in state — if any inbound message is logged for
    this contact after the last_sent_at timestamp, they've responded and we stop pinging.
    We also do a live GHL check for recency.
    """
    last = last_sent_at(contact_id, state)
    if not last:
        return False

    # Check GHL conversations for any inbound message after our last text
    try:
        data = ghl_get(f'/conversations/?contactId={contact_id}&locationId={LOCATION_ID}&limit=1')
        convos = data.get('conversations', [])
        if not convos:
            return False

        conv_id  = convos[0].get('id', '')
        messages = []
        if conv_id:
            msg_data = ghl_get(f'/conversations/{conv_id}/messages')
            msgs = msg_data.get('messages', {})
            messages = msgs.get('messages', msgs) if isinstance(msgs, dict) else msgs

        for msg in messages:
            direction = (msg.get('direction') or '').lower()
            msg_type  = (msg.get('type') or msg.get('messageType') or '').lower()
            date_str  = msg.get('dateAdded') or msg.get('createdAt', '')
            is_inbound = direction == 'inbound' or 'incoming' in msg_type

            if not is_inbound or not date_str:
                continue
            try:
                msg_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if msg_dt > last:
                    return True
            except Exception:
                continue
    except Exception:
        pass

    return False


# ─── OUTBOUND ─────────────────────────────────────────────────────────────────

def get_active_leads(days_threshold: int, limit: int) -> list:
    """Fetch open opportunities from Supabase, quiet for X days, excluding dead stages."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_threshold)).isoformat()

    resp = requests.get(
        f'{SUPABASE_URL}/rest/v1/ghl_opportunities',
        headers=SB_HEADERS,
        params={
            'select': 'source_id,contact_id,contact_name,contact_phone,contact_email,'
                      'stage_name,pipeline_name,status,last_stage_change_at',
            'status':                'eq.open',
            'last_stage_change_at':  f'lt.{cutoff}',
            'order':                 'last_stage_change_at.asc',
            'limit':                 str(limit * 4),
        },
        timeout=20,
    )
    resp.raise_for_status()
    opps = resp.json()

    active = []
    seen_contacts = set()
    for opp in opps:
        if is_dead_stage(opp.get('stage_name')):
            continue
        cid = opp.get('contact_id')
        if not cid or cid in seen_contacts:
            continue
        seen_contacts.add(cid)
        active.append(opp)
        if len(active) >= limit:
            break

    return active


def get_contact_notes(contact_id: str) -> list:
    """Get notes fresh from GHL (newest first)."""
    try:
        data = ghl_get(f'/contacts/{contact_id}/notes/')
        notes = data.get('notes', [])
        return sorted(notes, key=lambda n: n.get('dateAdded', ''), reverse=True)
    except Exception:
        return []


def draft_outbound_text(opp: dict, notes: list) -> dict:
    """
    Claude drafts a personalized text on Ashley's behalf.
    The message must communicate motivation and give the lead a clear reason to reply.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    name       = opp.get('contact_name') or 'Lead'
    first_name = name.split()[0] if name else 'there'
    stage      = opp.get('stage_name', 'Unknown')
    pipeline   = opp.get('pipeline_name', '')
    context    = PIPELINE_CONTEXT.get(pipeline, 'a real estate lead')

    notes_text = '\n\n'.join(
        f'[{n.get("dateAdded", "")[:10]}] {(n.get("body") or "").strip()}'
        for n in notes[:8]
        if n.get('body')
    ) or '(No notes on file — draft based on context alone)'

    prompt = f"""You are writing a text message on behalf of Ashley Diep, a real estate agent and recruiter in Houston.

Lead: {name} (use first name: {first_name})
Context: {context}
Current pipeline stage: {stage}

Notes on file about this lead:
{notes_text}

Write a text message Ashley will send to this lead TODAY. The message must:
1. Feel like it came from a real person — warm, direct, no fluff
2. Reference something SPECIFIC from the notes if anything meaningful is there
3. State Ashley's motivation — why she's reaching out right now (not just "checking in")
4. Give the lead a CLEAR reason to respond — a question, a hook, something valuable
5. Be 2-4 sentences MAX. This is a text, not an email.
6. Sound like Ashley — real estate agent, recruiter, action-oriented, no corporate speak
7. Use first name only, no emojis unless it naturally fits the tone of the conversation

Return JSON only:
{{
  "message": "the text message to send",
  "priority": "high|medium|low",
  "why": "1 sentence — what in the notes drove this specific message"
}}"""

    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=500,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return parse_json_from_claude(msg.content[0].text.strip())


def send_ghl_sms(contact_id: str, message: str) -> bool:
    """Send an SMS via GHL conversations API. Returns True on success."""
    try:
        ghl_post('/conversations/messages', {
            'type':        'SMS',
            'contactId':   contact_id,
            'locationId':  LOCATION_ID,
            'message':     message,
        })
        return True
    except Exception as e:
        print(f'  [!] GHL SMS failed: {e}')
        return False


def format_outbound_sent_log(opp: dict, draft: dict) -> str:
    name     = opp.get('contact_name') or 'Unknown'
    phone    = opp.get('contact_phone') or '—'
    stage    = opp.get('stage_name') or '—'
    pipeline = opp.get('pipeline_name') or '—'
    cid      = opp.get('contact_id') or ''
    priority = draft.get('priority', 'medium').upper()
    message  = draft.get('message', '')
    why      = draft.get('why', '')

    emoji    = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(priority, '⚪')
    ghl_link = (
        f'https://app.gohighlevel.com/v2/location/{LOCATION_ID}/contacts/detail/{cid}'
        if cid else ''
    )

    lines = [
        f'{emoji} *Sent to {name}* — {priority}',
        f'📞 {phone}  |  {stage} ({pipeline})',
        '',
        f'*Message sent:*',
        f'`{message}`',
        '',
        f'_{why}_',
    ]
    if ghl_link:
        lines.append(f'[Open in GHL]({ghl_link})')

    return '\n'.join(lines)


def run_outbound(days: int, limit: int, dry_run: bool):
    print(f'\n[outbound] Finding open leads quiet for {days}+ days...')
    state = load_state()
    leads = get_active_leads(days, limit)

    if not leads:
        print('[outbound] No leads found.')
        if not dry_run:
            send_telegram(
                f'✅ *Outbound Follow-Up*\n'
                f'No active leads have been quiet for {days}+ days. Pipeline is fresh!'
            )
        return

    print(f'[outbound] Found {len(leads)} candidates.')

    # Skip leads on 60-day cooldown OR who have already replied since last text
    leads_to_send = []
    skipped_cooldown = 0
    skipped_responded = 0
    for lead in leads:
        cid = lead.get('contact_id', '')
        if on_repingcooldown(cid, state):
            skipped_cooldown += 1
            continue
        if has_responded_since_last_text(cid, state):
            skipped_responded += 1
            print(f'  {lead.get("contact_name")} already replied — removing from queue')
            # Clear their outbound_sent entry so they're treated fresh if they go cold again
            state.setdefault('outbound_sent', {}).pop(cid, None)
            continue
        leads_to_send.append(lead)
        time.sleep(0.2)  # gentle GHL rate limit during response checks

    if skipped_cooldown:
        print(f'[outbound] {skipped_cooldown} on 60-day cooldown.')
    if skipped_responded:
        print(f'[outbound] {skipped_responded} already responded — removed from re-ping queue.')

    if not leads_to_send:
        print('[outbound] All leads on cooldown — nothing to send.')
        return

    print(f'[outbound] Sending to {len(leads_to_send)} leads...')

    if not dry_run:
        send_telegram(
            f'📲 *Outbound Follow-Up — {len(leads_to_send)} texts sending now*\n'
            f'Active leads quiet for {days}+ days. Sending personalized texts...'
        )

    sent_count = 0
    outbound_log = state.setdefault('outbound_sent', {})

    for opp in leads_to_send:
        name       = opp.get('contact_name') or 'Unknown'
        contact_id = opp.get('contact_id')

        if not contact_id:
            print(f'  Skipping {name} — no contact_id')
            continue

        print(f'  Drafting for {name}...')
        notes = get_contact_notes(contact_id)
        time.sleep(0.5)

        try:
            draft = draft_outbound_text(opp, notes)
        except Exception as e:
            print(f'  [!] Claude error for {name}: {e}')
            continue

        if dry_run:
            print(f'\n--- {name} ---')
            print(f'Priority: {draft.get("priority")}')
            print(f'Message: {draft.get("message")}')
            print(f'Why: {draft.get("why")}')
            sent_count += 1
            continue

        # Auto-send via GHL
        success = send_ghl_sms(contact_id, draft['message'])
        if not success:
            continue

        sent_ts = datetime.now(timezone.utc).isoformat()

        # Log timestamp so cooldown kicks in
        outbound_log[contact_id] = sent_ts

        # Persist to Supabase for durability + daily brief queries
        try:
            sb_post('outbound_sms_log', {
                'contact_id':   contact_id,
                'contact_name': opp.get('contact_name'),
                'pipeline':     opp.get('pipeline_name'),
                'stage':        opp.get('stage_name'),
                'message_body': draft['message'],
                'priority':     draft.get('priority'),
                'sent_at':      sent_ts,
            })
        except Exception as e:
            print(f'  [!] Supabase SMS log failed (non-fatal): {e}')

        # Notify Telegram what was sent
        log_msg = format_outbound_sent_log(opp, draft)
        send_telegram(log_msg)
        time.sleep(1)

        sent_count += 1

    if not dry_run:
        state['outbound_sent'] = outbound_log
        save_state(state)

    print(f'[outbound] Done — {sent_count} texts sent.')
    if not dry_run and sent_count > 0:
        send_telegram(f'✅ *{sent_count} text{"s" if sent_count != 1 else ""} sent.* Replies will be captured automatically when they come in.')


# ─── INBOUND ──────────────────────────────────────────────────────────────────

def get_recent_conversations(limit: int = 100) -> list:
    try:
        data = ghl_get(
            f'/conversations/?locationId={LOCATION_ID}'
            f'&limit={limit}&sortBy=last_message_date&sortOrder=desc'
        )
        return data.get('conversations', [])
    except Exception as e:
        print(f'[inbound] Error fetching conversations: {e}')
        return []


def get_conversation_messages(conv_id: str) -> list:
    try:
        data = ghl_get(f'/conversations/{conv_id}/messages')
        msgs = data.get('messages', {})
        # GHL v1 sometimes nests: { messages: { messages: [...] } }
        if isinstance(msgs, dict):
            return msgs.get('messages', [])
        return msgs if isinstance(msgs, list) else []
    except Exception:
        return []


def contact_is_active_lead(contact_id: str) -> bool:
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/ghl_opportunities',
            headers=SB_HEADERS,
            params={
                'select': 'stage_name',
                'contact_id': f'eq.{contact_id}',
                'status':     'eq.open',
                'limit':      '5',
            },
            timeout=10,
        )
        resp.raise_for_status()
        opps = resp.json()
        return any(not is_dead_stage(o.get('stage_name')) for o in opps)
    except Exception:
        return False


def get_contact_pipeline(contact_id: str) -> str:
    try:
        resp = requests.get(
            f'{SUPABASE_URL}/rest/v1/ghl_opportunities',
            headers=SB_HEADERS,
            params={
                'select':     'pipeline_name',
                'contact_id': f'eq.{contact_id}',
                'status':     'eq.open',
                'limit':      '1',
            },
            timeout=10,
        )
        resp.raise_for_status()
        opps = resp.json()
        return opps[0].get('pipeline_name', '') if opps else ''
    except Exception:
        return ''


def extract_reply_info(contact_name: str, reply_text: str, existing_notes: list, pipeline: str) -> dict:
    """Claude extracts key facts from a lead's reply and drafts a GHL note."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    context = PIPELINE_CONTEXT.get(pipeline, 'a real estate lead')
    existing = '\n'.join(
        f'[{n.get("dateAdded", "")[:10]}] {(n.get("body") or "").strip()}'
        for n in existing_notes[:5]
        if n.get('body')
    ) or '(none)'

    today = datetime.now().strftime('%Y-%m-%d')

    prompt = f"""You are Ashley Diep's AI assistant. Ashley is a real estate agent and recruiter in Houston.

A lead just replied to Ashley's text.
Lead: {contact_name}
Context: {context}
Today: {today}

Their reply:
"{reply_text}"

Existing notes on file:
{existing}

Extract every useful piece of information from this reply. Consider:
- Current situation, timeline, motivation
- Budget or price range (if mentioned)
- Pain points or objections raised
- Interest level signals (excited, hesitant, not ready, etc.)
- Specific questions they asked
- Any personal details useful for rapport or follow-up
- What next step is implied by their response

Return JSON only:
{{
  "note_update": "2-4 sentence note to add to their GHL record. Write in third person past tense. Start with 'Lead replied {today} —' then summarize what they said and all key facts extracted. Be specific.",
  "interest_level": "hot|warm|cold",
  "next_step": "Specific recommended action for Ashley (e.g. call them today, set appointment, send listing info, etc.)",
  "key_facts": ["fact1", "fact2", "fact3"]
}}"""

    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=600,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return parse_json_from_claude(msg.content[0].text.strip())


def store_pending_note(contact_id: str, contact_name: str, note_body: str,
                       reply_text: str, extraction: dict) -> str:
    """Store a pending note in Supabase. Returns the pending note ID."""
    pending_id = str(uuid.uuid4())
    sb_post('pending_notes', {
        'id':             pending_id,
        'contact_id':     contact_id,
        'contact_name':   contact_name,
        'note_body':      note_body,
        'reply_text':     reply_text,
        'interest_level': extraction.get('interest_level'),
        'next_step':      extraction.get('next_step'),
        'status':         'pending',
    })
    return pending_id


def format_inbound_approval_message(contact_name: str, contact_id: str,
                                    reply: str, extraction: dict,
                                    pending_id: str) -> tuple[str, dict]:
    """Returns (message_text, reply_markup) for Telegram inline approval keyboard."""
    interest  = extraction.get('interest_level', 'warm').upper()
    next_step = extraction.get('next_step', '')
    note      = extraction.get('note_update', '')
    facts     = extraction.get('key_facts', [])

    emoji = {'HOT': '🔥', 'WARM': '🟡', 'COLD': '❄️'}.get(interest, '⚪')
    preview = reply[:300] + ('...' if len(reply) > 300 else '')
    ghl_link = f'https://app.gohighlevel.com/v2/location/{LOCATION_ID}/contacts/detail/{contact_id}'

    lines = [
        f'{emoji} *{contact_name} replied* — {interest}',
        '',
        '*Their message:*',
        f'_{preview}_',
        '',
        '*Draft note for GHL:*',
        note,
    ]
    if facts:
        lines += ['', f'*Key facts:* {" · ".join(facts[:4])}']
    if next_step:
        lines += ['', f'*Next step:* {next_step}']
    lines += ['', f'[Open in GHL]({ghl_link})']
    lines += ['', '_Approve to add this note to GHL, or skip to discard._']

    reply_markup = {
        'inline_keyboard': [[
            {'text': '✅ Add to GHL', 'callback_data': f'approve_note:{pending_id}'},
            {'text': '❌ Skip',        'callback_data': f'skip_note:{pending_id}'},
        ]]
    }

    return '\n'.join(lines), reply_markup


def run_inbound(dry_run: bool):
    print('\n[inbound] Scanning conversations for new lead replies...')
    state = load_state()
    processed_ids = set(state.get('processed_message_ids', []))

    last_check = state.get('last_inbound_check')
    last_check_dt = (
        datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        if last_check
        else datetime.now(timezone.utc) - timedelta(hours=24)
    )

    convos = get_recent_conversations(limit=100)
    print(f'[inbound] Checking {len(convos)} recent conversations...')

    captures = 0
    new_processed_ids = list(processed_ids)

    for conv in convos:
        contact_id   = conv.get('contactId') or (conv.get('contact') or {}).get('id')
        contact_name = conv.get('contactName') or (conv.get('contact') or {}).get('name') or 'Unknown'

        if not contact_id:
            continue

        # Quick skip: if last message is old and no unread, skip API call
        last_msg_date = conv.get('lastMessageDate', '')
        if last_msg_date and conv.get('unreadCount', 0) == 0:
            try:
                lmd = datetime.fromisoformat(last_msg_date.replace('Z', '+00:00'))
                if lmd <= last_check_dt:
                    continue
            except Exception:
                pass

        if not contact_is_active_lead(contact_id):
            continue

        messages = get_conversation_messages(conv.get('id', ''))
        time.sleep(0.3)

        # Find new inbound messages not yet processed
        new_inbound = []
        for msg in messages:
            msg_id    = msg.get('id')
            direction = (msg.get('direction') or '').lower()
            msg_type  = (msg.get('type') or msg.get('messageType') or '').lower()
            body      = (msg.get('body') or msg.get('message') or '').strip()
            date_str  = msg.get('dateAdded') or msg.get('createdAt', '')

            is_inbound = (
                direction == 'inbound'
                or 'incoming' in msg_type
                or 'inbound' in msg_type
            )
            if not is_inbound or not body:
                continue
            if msg_id and msg_id in processed_ids:
                continue
            if date_str:
                try:
                    msg_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if msg_dt <= last_check_dt:
                        continue
                except Exception:
                    pass

            new_inbound.append(msg)

        if not new_inbound:
            continue

        # Process only the most recent inbound
        latest     = max(new_inbound, key=lambda m: m.get('dateAdded') or m.get('createdAt', ''))
        reply_text = (latest.get('body') or latest.get('message') or '').strip()

        if not reply_text:
            continue

        print(f'  New reply from {contact_name}: {reply_text[:60]}...')

        notes    = get_contact_notes(contact_id)
        pipeline = get_contact_pipeline(contact_id)

        try:
            extraction = extract_reply_info(contact_name, reply_text, notes, pipeline)
        except Exception as e:
            print(f'  [!] Claude error for {contact_name}: {e}')
            continue

        today     = datetime.now().strftime('%Y-%m-%d')
        note_body = f'[AI Captured — {today}]\n{extraction.get("note_update", reply_text)}'

        if dry_run:
            print(f'\n--- {contact_name} ---')
            print(f'Reply: {reply_text}')
            print(f'Interest: {extraction.get("interest_level")}')
            print(f'Note draft: {extraction.get("note_update")}')
            print(f'Next step: {extraction.get("next_step")}')
        else:
            try:
                pending_id = store_pending_note(
                    contact_id, contact_name, note_body, reply_text, extraction
                )
            except Exception as e:
                print(f'  [!] Supabase store failed for {contact_name}: {e}')
                continue

            tg_text, reply_markup = format_inbound_approval_message(
                contact_name, contact_id, reply_text, extraction, pending_id
            )
            send_telegram(tg_text, reply_markup)
            time.sleep(0.5)

        for m in new_inbound:
            if m.get('id'):
                new_processed_ids.append(m['id'])

        captures += 1

    if not dry_run:
        state['last_inbound_check']     = datetime.now(timezone.utc).isoformat()
        state['processed_message_ids']  = new_processed_ids[-1000:]
        save_state(state)

    if captures == 0:
        print('[inbound] No new replies found.')
    else:
        print(f'[inbound] {captures} new repl{"ies" if captures != 1 else "y"} sent to Telegram for approval.')

    return captures


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Lead follow-up AI — auto-send outbound texts + capture inbound replies'
    )
    parser.add_argument('--mode', choices=['outbound', 'inbound', 'both'], default='both')
    parser.add_argument('--days', type=int, default=180,
                        help='Outbound: leads quiet this many days (default: 180)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Outbound: max contacts per run (default: 10)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print everything — no GHL writes, no Telegram sends')
    args = parser.parse_args()

    if args.mode in ('outbound', 'both'):
        run_outbound(args.days, args.limit, args.dry_run)

    if args.mode in ('inbound', 'both'):
        run_inbound(args.dry_run)


if __name__ == '__main__':
    main()
