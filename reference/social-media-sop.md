# Social Media Content SOP

**Owner:** Ashley Diep
**Platforms:** Facebook, YouTube, Instagram
**Cadence:** Weekly — generated every Monday automatically
**Time required:** 5–10 minutes Monday to review and schedule

---

## Overview

The AI OS generates a full week of social media content every Monday morning. Ashley reviews, edits if needed, and schedules. The system handles the thinking. Ashley handles the judgment calls on tone and timing.

Goal: consistent seller-targeting content on all three platforms without spending hours on it each week.

---

## Weekly Workflow

### Step 1 — Review (Monday, 5-10 min)

Open the three draft files generated in `outputs/social/`:

| Platform | File location |
|----------|---------------|
| Facebook | `outputs/social/facebook/YYYY-MM-DD-week.md` |
| YouTube | `outputs/social/youtube/YYYY-MM-DD-week.md` |
| Instagram | `outputs/social/instagram/YYYY-MM-DD-week.md` |

Read each post. Edit anything that doesn't sound like you. The AI knows your niches and tone but you have the final say on style.

Change the status line from `DRAFT — Pending Review` to `APPROVED` when done.

### Step 2 — Schedule Posts (Monday, 10-15 min)

Use **Buffer** or **Later** to schedule the week:

| Platform | Posts per week | Recommended days | Best times (CT) |
|----------|---------------|-----------------|-----------------|
| Facebook | 4 | Mon, Tue, Thu, Sat | 9am or 6pm |
| Instagram | 4 | Mon, Wed, Fri, Sun | 12pm or 6pm |
| YouTube | 2 videos | Tue, Thu | 12pm |

Copy captions directly from the draft files. For Instagram, include the hashtags from the file.

### Step 3 — YouTube Video Production

The YouTube file contains a title, hook, outline, and CTA — not a finished script. Use it to:

1. Record the video (the hook is word-for-word what to say in the first 30 seconds)
2. Follow the outline for the body
3. Use the CTA as written at the end
4. Upload the finished video to **Google Drive**: `HIGHKEY/Social Media/[Month-Year]/`
5. Note the video link back in the YouTube draft file

### Step 4 — Archive

After the week's posts are scheduled and videos recorded:

- Move all three week files from `outputs/social/[platform]/` to `outputs/social/archive/`
- Add a one-line note at the top of each file about what resonated (optional — helps the AI improve future posts)

---

## Content Mix (per week)

| Platform | # Posts | Mix |
|----------|---------|-----|
| Facebook | 4 | 1 seller tip · 1 market insight · 1 seller CTA · 1 entertaining |
| Instagram | 4 | 1 seller tip · 1 seller CTA · 1 agent recruitment · 1 reel concept |
| YouTube | 2 | 1 seller education or market update · 1 BTS or myth-buster |

---

## Editing Style Guide

When editing generated posts, keep these principles:

- **Direct and punchy** — if a sentence doesn't add value, cut it
- **Speak to pain** — sellers care about price, timeline, and stress. Hit those buttons.
- **First person** — Ashley is speaking, not a brand account
- **CTAs that feel natural** — "Thinking about selling? DM me." not "Contact us today!"
- **Instagram hashtags** — keep the mix: broad (`#realestate #houstonrealestate`) + niche (`#sellingyourhome #houstonhomes #fsbo`)

---

## Folder Structure

```
outputs/social/
├── facebook/         ← Current week Facebook drafts
├── youtube/          ← Current week YouTube drafts
├── instagram/        ← Current week Instagram drafts
└── archive/          ← Approved and scheduled posts
```

Edited video files (MP4s, raw footage) live in **Google Drive**, not this project.

---

## Automation

The content script runs via a scheduled Routine on Anthropic's cloud every Monday at 7:00 AM CT.

To run it manually at any time:
```bash
python scripts/social-content.py
```

Requires `ANTHROPIC_API_KEY` in your `.env.local`.

---

## Handing to a VA

When you're ready to delegate scheduling:

1. Share this SOP with your VA
2. Give them access to `outputs/social/` (share via Google Drive or Notion export)
3. Give them Buffer/Later access
4. Ashley still reviews drafts — VA schedules after approval
5. VA also handles uploading reviewed videos to Google Drive

The VA never writes content. They schedule what the system generates and Ashley approves.

---

*Update this SOP whenever the workflow changes. Last updated: 2026-04-25*
