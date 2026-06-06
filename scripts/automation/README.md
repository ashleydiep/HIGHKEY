# Agent Attraction Automation

Three scripts that run your agent attraction system on autopilot.

---

## 1. Calendar → GHL Contacts (`calendar_to_ghl.py`)

Watches Google Calendar for meetings. If an attendee's email isn't already in GoHighLevel, creates a contact named `<Name> + Michelle Wilson` and tags it `calendar-import`.

**Run manually:**
```bash
cd proagent-os
python3 scripts/automation/calendar_to_ghl.py
```

**Options:**
```bash
--days 7       # How far back/forward to scan (default: 7)
--dry-run      # Preview without creating contacts
```

**To automate:** Add to your daily `/sync` command or schedule as a Routine.

---

## 2. Meeting Transcriber (`meeting_transcriber.py`)

Drop a meeting recording file anywhere, pass it to this script, and it will:
1. Transcribe with Groq Whisper (free, fast)
2. Generate structured notes with Claude (summary, action items, insights, follow-up timing)
3. Add notes to the contact's GHL profile
4. Send the notes to your Telegram

**Drop recordings here:** `~/meeting-recordings/inbox/`

**Run:**
```bash
# Auto-detect contact from transcript
python3 scripts/automation/meeting_transcriber.py ~/meeting-recordings/inbox/call-john.mp4

# Specify contact explicitly
python3 scripts/automation/meeting_transcriber.py ~/meeting-recordings/inbox/call-john.mp4 --email john@kw.com
python3 scripts/automation/meeting_transcriber.py ~/meeting-recordings/inbox/call-john.mp4 --contact-name "John Smith"
python3 scripts/automation/meeting_transcriber.py ~/meeting-recordings/inbox/call-john.mp4 --contact-id ghl_id_here
```

**Supported formats:** mp3, mp4, m4a, wav, mov, webm

---

## 3. Re-engagement (`reengage.py`)

Finds contacts that haven't been touched in 60+ days, reads their GHL notes, and drafts a personalized re-engagement message with Claude. Sends everything to your Telegram for review.

**Run manually:**
```bash
python3 scripts/automation/reengage.py
python3 scripts/automation/reengage.py --days 90   # longer threshold
python3 scripts/automation/reengage.py --dry-run   # print without sending
```

**To automate:** Schedule as a weekly Routine (e.g., every Monday morning).

---

## Folder Structure

```
~/meeting-recordings/
├── inbox/      ← Drop recordings here
└── processed/  ← Moved here after transcription

proagent-os/data/sync-state/
└── calendar_ghl.json  ← Tracks which calendar events were already processed
```

---

## Dependencies

All already installed. Requires:
- `google-auth`, `google-auth-oauthlib`, `google-api-python-client` (calendar auth)
- `anthropic` (Claude)
- `groq` (Whisper transcription)
- `requests`
- `imageio-ffmpeg` or system `ffmpeg` (audio extraction)
