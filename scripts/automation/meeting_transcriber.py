#!/usr/bin/env python3
"""
Meeting Transcriber + GHL Note Updater
Transcribes a meeting recording, extracts structured notes with Claude,
adds them to the contact's GHL profile, and sends a summary to Ashley via Telegram.

Usage:
  python3 meeting_transcriber.py <audio_file>
  python3 meeting_transcriber.py <audio_file> --email john@example.com
  python3 meeting_transcriber.py <audio_file> --contact-id ghl_contact_id_here
  python3 meeting_transcriber.py <audio_file> --contact-name "John Smith"

Drop recordings in ~/meeting-recordings/inbox/ and they'll be moved to ~/meeting-recordings/processed/ after.

Examples:
  python3 meeting_transcriber.py ~/meeting-recordings/inbox/call-john-2026-05-15.mp4
  python3 meeting_transcriber.py ~/meeting-recordings/inbox/call-john.m4a --email john@kw.com
"""
import sys
import json
import argparse
import subprocess
import tempfile
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

import requests
import anthropic
from agent_config import load_config
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = 'ffmpeg'

CFG = load_config()

ANTHROPIC_KEY    = CFG['anthropic_api_key']
GROQ_API_KEY     = CFG.get('groq_api_key', '')
GHL_KEY          = CFG['ghl_api_key']
LOCATION_ID      = CFG['ghl_location_id']
TELEGRAM_TOKEN   = CFG.get('telegram_bot_token', '')
TELEGRAM_CHAT_ID = CFG.get('notification_telegram_chat_id')
GHL_BASE = 'https://rest.gohighlevel.com/v1'
GHL_HEADERS = {'Authorization': f'Bearer {GHL_KEY}', 'Content-Type': 'application/json'}

INBOX_DIR = Path.home() / 'meeting-recordings' / 'inbox'
PROCESSED_DIR = Path.home() / 'meeting-recordings' / 'processed'


# ─── Audio extraction ─────────────────────────────────────────────────────────

def extract_audio(input_path: str, tmp_dir: str) -> str:
    ext = Path(input_path).suffix.lower()
    if ext in ['.mp3', '.m4a', '.wav', '.ogg', '.flac', '.webm']:
        return input_path

    print('  Extracting audio from video...')
    audio_path = os.path.join(tmp_dir, 'audio.mp3')
    result = subprocess.run(
        [FFMPEG, '-i', input_path, '-vn', '-ar', '16000', '-ac', '1',
         '-b:a', '64k', audio_path, '-y', '-loglevel', 'error'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f'  ffmpeg error: {result.stderr}')
        sys.exit(1)
    return audio_path


def get_duration(file_path: str) -> int:
    try:
        result = subprocess.run(
            [FFMPEG, '-i', file_path, '-f', 'null', '-'],
            capture_output=True, text=True,
        )
        for line in result.stderr.splitlines():
            if 'Duration:' in line:
                t = line.split('Duration:')[1].split(',')[0].strip()
                h, m, s = t.split(':')
                return int(float(h) * 3600 + float(m) * 60 + float(s))
    except Exception:
        pass
    return 0


# ─── Transcription ────────────────────────────────────────────────────────────

def transcribe(audio_path: str) -> str:
    file_size = os.path.getsize(audio_path)
    size_mb = file_size / 1024 / 1024
    print(f'  Transcribing ({size_mb:.1f} MB)...')

    if not GROQ_API_KEY:
        print('  ERROR: GROQ_API_KEY not set. Add it to .env.local')
        sys.exit(1)

    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    if file_size > 24 * 1024 * 1024:
        return _chunk_and_transcribe(audio_path, client)

    with open(audio_path, 'rb') as f:
        result = client.audio.transcriptions.create(
            file=(Path(audio_path).name, f),
            model='whisper-large-v3',
            language='en',
            response_format='text',
        )
    return result if isinstance(result, str) else result.text


def _chunk_and_transcribe(audio_path: str, client) -> str:
    print('  File >25 MB — splitting into 20-min segments...')
    tmp_dir = tempfile.mkdtemp()
    chunk_pattern = os.path.join(tmp_dir, 'chunk_%03d.mp3')
    subprocess.run([
        FFMPEG, '-i', audio_path, '-f', 'segment',
        '-segment_time', '1200', '-ar', '16000', '-ac', '1',
        '-b:a', '64k', chunk_pattern, '-y', '-loglevel', 'error',
    ], check=True)

    chunks = sorted(Path(tmp_dir).glob('chunk_*.mp3'))
    transcripts = []
    for i, chunk in enumerate(chunks):
        print(f'  Transcribing chunk {i + 1}/{len(chunks)}...')
        with open(chunk, 'rb') as f:
            result = client.audio.transcriptions.create(
                file=(chunk.name, f),
                model='whisper-large-v3',
                language='en',
                response_format='text',
            )
        transcripts.append(result if isinstance(result, str) else result.text)
    shutil.rmtree(tmp_dir)
    return ' '.join(transcripts)


# ─── AI note generation ───────────────────────────────────────────────────────

def generate_meeting_notes(transcript: str, contact_name: str, meeting_date: str) -> dict:
    print('  Generating meeting notes with Claude...')
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    prompt = f"""You are Ashley Diep's AI assistant. Ashley is a real estate agent and recruiter.
She met with {contact_name or 'a contact'} on {meeting_date}.

Analyze this meeting transcript and return structured notes in JSON:

{{
  "summary": "2-3 sentence overview of what the meeting covered",
  "key_points": [
    "important thing discussed 1",
    "important thing discussed 2"
  ],
  "action_items": [
    "follow-up action for Ashley",
    "follow-up action for the contact"
  ],
  "contact_insights": {{
    "current_situation": "what is their current role/situation",
    "pain_points": "what challenges did they mention",
    "goals": "what are they trying to achieve",
    "interest_level": "hot/warm/cold based on conversation",
    "next_best_move": "recommended next step"
  }},
  "follow_up_timing": "when to follow up (e.g., 'in 1 week', 'next month')"
}}

Transcript:
{transcript[:15000]}"""

    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        messages=[{'role': 'user', 'content': prompt}],
    )
    text = message.content[0].text.strip()
    start, end = text.find('{'), text.rfind('}') + 1
    return json.loads(text[start:end])


def format_ghl_note(notes: dict, contact_name: str, meeting_date: str, duration_secs: int) -> str:
    duration_min = duration_secs // 60
    lines = [
        f'=== Meeting Notes: {meeting_date} ({duration_min} min) ===',
        '',
        f'SUMMARY',
        notes.get('summary', ''),
        '',
        'KEY POINTS',
    ]
    for pt in notes.get('key_points', []):
        lines.append(f'• {pt}')

    lines += ['', 'ACTION ITEMS']
    for item in notes.get('action_items', []):
        lines.append(f'☐ {item}')

    insights = notes.get('contact_insights', {})
    if insights:
        lines += ['', 'CONTACT INSIGHTS']
        for k, v in insights.items():
            if v:
                label = k.replace('_', ' ').title()
                lines.append(f'{label}: {v}')

    follow_up = notes.get('follow_up_timing', '')
    if follow_up:
        lines += ['', f'FOLLOW UP: {follow_up}']

    return '\n'.join(lines)


def format_telegram_message(notes: dict, contact_name: str, meeting_date: str, ghl_updated: bool) -> str:
    insights = notes.get('contact_insights', {})
    action_items = notes.get('action_items', [])
    actions_text = '\n'.join(f'  ☐ {a}' for a in action_items[:5]) if action_items else '  (none)'
    ghl_status = '✅ GHL updated' if ghl_updated else '⚠️ GHL not updated (contact not found)'

    return (
        f'📋 *Meeting Notes: {contact_name or "Unknown"}*\n'
        f'📅 {meeting_date}\n'
        f'{ghl_status}\n\n'
        f'*Summary:*\n{notes.get("summary", "")}\n\n'
        f'*Interest Level:* {insights.get("interest_level", "unknown").upper()}\n'
        f'*Next Best Move:* {insights.get("next_best_move", "")}\n'
        f'*Follow Up:* {notes.get("follow_up_timing", "")}\n\n'
        f'*Action Items:*\n{actions_text}'
    )


# ─── GHL ──────────────────────────────────────────────────────────────────────

def search_ghl_by_email(email: str) -> Optional[dict]:
    resp = requests.get(
        f'{GHL_BASE}/contacts/',
        headers=GHL_HEADERS,
        params={'query': email, 'locationId': LOCATION_ID},
        timeout=15,
    )
    resp.raise_for_status()
    contacts = resp.json().get('contacts', [])
    for c in contacts:
        if (c.get('email') or '').lower() == email.lower():
            return c
    return None


def search_ghl_by_name(name: str) -> Optional[dict]:
    resp = requests.get(
        f'{GHL_BASE}/contacts/',
        headers=GHL_HEADERS,
        params={'query': name, 'locationId': LOCATION_ID},
        timeout=15,
    )
    resp.raise_for_status()
    contacts = resp.json().get('contacts', [])
    if contacts:
        return contacts[0]
    return None


def get_ghl_contact_by_id(contact_id: str) -> Optional[dict]:
    resp = requests.get(f'{GHL_BASE}/contacts/{contact_id}', headers=GHL_HEADERS, timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    return data.get('contact', data)


def add_ghl_note(contact_id: str, body: str):
    resp = requests.post(
        f'{GHL_BASE}/contacts/{contact_id}/notes/',
        headers=GHL_HEADERS,
        json={'body': body},
        timeout=15,
    )
    resp.raise_for_status()


def find_contact_from_transcript(transcript: str) -> Optional[dict]:
    """Ask Claude to extract a person's name/email from the transcript, then search GHL."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=200,
        messages=[{
            'role': 'user',
            'content': (
                'Extract the name and email of the MAIN CONTACT (not Ashley) from this meeting transcript. '
                'Return only JSON: {"name": "...", "email": "..."} or {"name": "...", "email": null} if no email found.\n\n'
                f'Transcript (first 3000 chars):\n{transcript[:3000]}'
            ),
        }],
    )
    text = message.content[0].text.strip()
    try:
        start, end = text.find('{'), text.rfind('}') + 1
        data = json.loads(text[start:end])
        name = data.get('name', '')
        email = data.get('email', '')

        if email:
            contact = search_ghl_by_email(email)
            if contact:
                return contact
        if name:
            contact = search_ghl_by_name(name)
            if contact:
                return contact
    except Exception:
        pass
    return None


# ─── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(text: str):
    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
        json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'},
        timeout=15,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Transcribe meeting + update GHL contact')
    parser.add_argument('source', help='Audio/video file path')
    parser.add_argument('--email', help='Contact email in GHL')
    parser.add_argument('--contact-id', help='GHL contact ID (skips search)')
    parser.add_argument('--contact-name', help='Contact name for search and notes')
    parser.add_argument('--date', default=str(date.today()), help='Meeting date (YYYY-MM-DD)')
    args = parser.parse_args()

    file_path = os.path.expanduser(args.source)
    if not os.path.exists(file_path):
        print(f'File not found: {file_path}')
        sys.exit(1)

    print(f'\nMeeting Transcriber')
    print(f'  File : {file_path}')
    print(f'  Date : {args.date}\n')

    tmp_dir = tempfile.mkdtemp()
    try:
        duration = get_duration(file_path)
        print(f'  Duration: {duration // 60}m {duration % 60}s')

        audio_path = extract_audio(file_path, tmp_dir)
        transcript = transcribe(audio_path)
        print(f'  Transcript: {len(transcript):,} chars')

        # Find GHL contact
        contact = None
        contact_name = args.contact_name or ''

        if args.contact_id:
            contact = get_ghl_contact_by_id(args.contact_id)
            if contact:
                contact_name = contact.get('contactName') or contact_name
                print(f'  Contact: {contact_name} (by ID)')
        elif args.email:
            contact = search_ghl_by_email(args.email)
            if contact:
                contact_name = contact.get('contactName') or contact_name
                print(f'  Contact: {contact_name} (by email)')
        elif args.contact_name:
            contact = search_ghl_by_name(args.contact_name)
            if contact:
                contact_name = contact.get('contactName') or contact_name
                print(f'  Contact: {contact_name} (by name)')
        else:
            print('  No contact specified — auto-detecting from transcript...')
            contact = find_contact_from_transcript(transcript)
            if contact:
                contact_name = contact.get('contactName') or contact_name
                print(f'  Auto-detected contact: {contact_name}')

        if not contact:
            print(f'  Contact not found in GHL — notes will be sent to Telegram only')

        notes = generate_meeting_notes(transcript, contact_name or 'Contact', args.date)

        # Add note to GHL
        ghl_updated = False
        if contact:
            contact_id = contact.get('id', '')
            note_body = format_ghl_note(notes, contact_name, args.date, duration)
            try:
                add_ghl_note(contact_id, note_body)
                ghl_updated = True
                print(f'  GHL note added to: {contact_name}')
            except Exception as e:
                print(f'  Warning: Could not add GHL note — {e}')

        # Send Telegram
        tg_message = format_telegram_message(notes, contact_name or 'Unknown', args.date, ghl_updated)
        send_telegram(tg_message)
        print(f'  Meeting notes sent to Telegram')

        # Move to processed
        processed_path = PROCESSED_DIR / Path(file_path).name
        if str(INBOX_DIR) in str(Path(file_path).resolve()):
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(file_path, processed_path)
            print(f'  Moved to processed: {processed_path.name}')

        print(f'\nDone. Meeting notes for "{contact_name or "unknown contact"}" processed.\n')

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
