#!/usr/bin/env python3
"""
Weekly social media content generator for PROAGENT / HIGHKEY.
Generates posts for Facebook, YouTube, and Instagram targeting Houston home sellers.

Output:
  outputs/social/facebook/YYYY-MM-DD-week.md
  outputs/social/youtube/YYYY-MM-DD-week.md
  outputs/social/instagram/YYYY-MM-DD-week.md

All files marked DRAFT - Pending Review until Ashley approves.

Usage:
  python scripts/social-content.py
"""

import anthropic
import os
from datetime import datetime, timedelta
from pathlib import Path

# Load .env.local from project root
env_path = Path(__file__).parent.parent / ".env.local"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

client = anthropic.Anthropic()

BUSINESS_CONTEXT = """
You are generating social media content for Ashley Diep, a Houston real estate agent.

Business: PROAGENT — Ashley helps sellers sell homes for maximum money in their desired timeline,
and helps buyers get great deals.

Target seller niches:
- Primary: Sellers with homes above $350k in the Houston area
- Distressed sellers (foreclosure, forbearance)
- Absentee owners
- Out-of-state owners
- Move-up owners (selling to buy bigger)
- Retired owners
- Downsizers

Tone: Direct, confident, no fluff. Ashley speaks to seller pain points with authority.
She is approachable but results-driven. Conversational — not corporate.

Content mix per week:
- 30% seller education and value (tips, myths busted, market insights)
- 30% entertaining reels for my listings
- 20% CTA posts (what's your home worth, thinking about selling)
- 20% entertaining or relatable real estate content (humor, surprising facts, relatable situations)
"""

FACEBOOK_PROMPT = """
Generate 4 Facebook posts for the week. Label them clearly as POST 1 through POST 4.

Mix:
- POST 1: Seller tip or myth-buster (educate)
- POST 2: Market insight or Houston-specific real estate fact or listing related (build authority)
- POST 3: Direct CTA targeting sellers (drive leads)
- POST 4: Entertaining or relatable real estate content (build audience)

Rules for each post:
- Caption: 3-5 sentences max, direct and punchy, no corporate speak, end with a question or CTA, first person as Ashley, no hashtags
- Visual: A specific, practical description of what Ashley should film or photograph to go with this post. Should look authentic — not stock photo. Examples: filming herself talking to camera in the car, a quick walkthrough of a listing, a photo at a kitchen table reviewing paperwork, a short clip walking through a neighborhood.

Format exactly like this:

POST 1 — Seller Tip
Caption: ...
Visual: ...

POST 2 — Market Insight or Listing
Caption: ...
Visual: ...

POST 3 — CTA
Caption: ...
Visual: ...

POST 4 — Entertaining
Caption: ...
Visual: ...
"""

YOUTUBE_PROMPT = """
Generate 3 YouTube video concepts for the week. Label them VIDEO 1, VIDEO 2, and VIDEO 3.

VIDEO 1 and VIDEO 2 target sellers:
- Seller education (mistakes sellers make, what to do before listing, pricing strategy)
- Houston market update (what sellers need to know right now)
- Behind the scenes at a listing appointment
- Myth-busting (common seller misconceptions)

VIDEO 3 targets real estate agents for recruitment. Ashley is building her brokerage (COLLAB) and wants agents to see what she's doing and want in. Pick one of these angles:
- How Ashley uses AI systems to run her real estate business (cold calling + AI follow-up, AI OS, automation)
- Raw behind the scenes of cold calling (what it actually looks like, the mindset, the numbers game)
- Closing a deal — what happened from first contact to commission check
- What Ashley's day actually looks like as an agent + recruiter running multiple businesses
- Why Ashley left or would leave a traditional brokerage (speak to agent pain points: splits, no support, no training)
- What agents get access to at her brokerage that they can't get anywhere else (daily training, ISA support, AI systems, Chad Cooley coaching)

For VIDEO 3, the CTA should drive agents to DM Ashley or book a call to learn more about joining.

For each video provide:
- Title: SEO-friendly, curiosity-driven, under 60 characters
- Hook: First 30 seconds script — what Ashley says to stop the scroll and keep them watching
- Outline: 4-5 bullet points covering the video body
- CTA: What to say at the end

Format exactly like this:

VIDEO 1 — Seller [Type]
Title: ...
Hook: ...
Outline:
• ...
• ...
• ...
• ...
CTA: ...

VIDEO 2 — Seller [Type]
Title: ...
Hook: ...
Outline:
• ...
• ...
• ...
• ...
CTA: ...

VIDEO 3 — Agent Recruitment [Type]
Title: ...
Hook: ...
Outline:
• ...
• ...
• ...
• ...
CTA: ...
"""

INSTAGRAM_PROMPT = """
Generate 4 Instagram posts for the week. Label them POST 1 through POST 4.

Mix:
- POST 1: Seller tip (educational — works as a static post or carousel)
- POST 2: Seller pain point CTA (targets motivated sellers)
- POST 3: Agent recruitment (for agents looking for a better brokerage or more support)
- POST 4: Reel — entertaining or relatable real estate content

For every post provide:
- Visual: A specific, practical description of what Ashley should film or photograph. Should look real and authentic — not stock photo. Be specific: "film yourself in the car after a listing appointment talking directly to camera", "photograph the front of a listing with a sold sign", "film a quick 3-second walk through a staged living room". For carousels, describe each slide briefly.
- Caption: 3-4 punchy sentences, conversational, first person as Ashley
- Hashtags: 12-15 relevant tags (mix broad + Houston-specific + niche)

Format exactly like this:

POST 1 — Seller Tip
Visual: ...
Caption: ...
Hashtags: ...

POST 2 — Seller CTA
Visual: ...
Caption: ...
Hashtags: ...

POST 3 — Agent Recruitment
Visual: ...
Caption: ...
Hashtags: ...

POST 4 — Reel
Visual: ...
Caption: ...
Hashtags: ...
"""


def generate_content(platform: str, prompt: str) -> str:
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2000,
        system=BUSINESS_CONTEXT,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def save_weekly_content(platform: str, content: str, week_start: datetime) -> Path:
    date_str = week_start.strftime("%Y-%m-%d")
    output_dir = Path(f"outputs/social/{platform}")
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / f"{date_str}-week.md"

    header = f"""# {platform.capitalize()} — Week of {week_start.strftime("%B %d, %Y")}

> **STATUS: DRAFT — Pending Review**
> Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
>
> Review each post. Edit tone/style as needed.
> Once approved, schedule in Buffer or Later and move this file to `outputs/social/archive/`.

---

"""
    filepath.write_text(header + content + "\n")
    return filepath


def main():
    today = datetime.now()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    print(f"Generating social content for week of {week_start.strftime('%B %d, %Y')}...")
    print()

    platforms = [
        ("facebook", FACEBOOK_PROMPT),
        ("youtube", YOUTUBE_PROMPT),
        ("instagram", INSTAGRAM_PROMPT),
    ]

    saved_files = []
    for platform, prompt in platforms:
        print(f"  [{platform.upper()}] Generating...")
        content = generate_content(platform, prompt)
        filepath = save_weekly_content(platform, content, week_start)
        saved_files.append(filepath)
        print(f"  [{platform.upper()}] Saved → {filepath}")

    print()
    print("Done. Review your posts:")
    for f in saved_files:
        print(f"  {f}")


if __name__ == "__main__":
    main()
