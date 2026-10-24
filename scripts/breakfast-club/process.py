#!/usr/bin/env python3
"""
Breakfast Club Sales Training Pipeline
Usage:
  python3 process.py <file_or_url>  [--date YYYY-MM-DD] [--title "Session Title"]

Examples:
  python3 process.py ~/breakfast-club/inbox/april-29.mp4
  python3 process.py ~/breakfast-club/inbox/april-29.mp4 --date 2026-04-29 --title "Handling Price Objections"
  python3 process.py "https://www.facebook.com/video/..." --date 2026-04-29
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import shutil
from datetime import date, datetime
from pathlib import Path

import anthropic
import voyageai
import requests
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"  # fallback to system ffmpeg if installed

# ── Credentials ───────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")  # fallback if Groq not set
VOYAGE_API_KEY    = os.environ.get("VOYAGE_API_KEY", "")
SUPABASE_URL      = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY      = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Transcription: Groq (free) is preferred. OpenAI Whisper is fallback.
# Get a free Groq key at console.groq.com — takes 2 min.

VALID_CATEGORIES = [
    "sellers", "buyers", "objection_handlers", "tonality",
    "mindset", "scripts", "concepts", "closing", "follow_up", "roleplay"
]

PROCESSED_DIR = Path.home() / "breakfast-club" / "processed"
INBOX_DIR     = Path.home() / "breakfast-club" / "inbox"


# ── Step 1: Download (if URL) ─────────────────────────────────────────────────
BROWSERS = ["chrome", "safari", "firefox", "edge"]

def download_from_facebook(url: str, tmp_dir: str) -> str:
    print(f"  Downloading from Facebook (using your browser login)...")
    out_path = os.path.join(tmp_dir, "session.%(ext)s")
    yt_dlp_bin = _find_yt_dlp()

    # Try each browser's cookie store until one works
    for browser in BROWSERS:
        cmd = [
            yt_dlp_bin,
            "--cookies-from-browser", browser,
            "-f", "bestaudio/best",
            "-o", out_path,
            "--no-playlist",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            for f in Path(tmp_dir).glob("session.*"):
                print(f"  Downloaded via {browser} cookies: {f.name}")
                return str(f)
        # Cookie error or browser not found — try next
        if "cookies" not in result.stderr.lower() and "browser" not in result.stderr.lower():
            # Real download error unrelated to cookies
            print(f"  Download error: {result.stderr[-500:]}")
            sys.exit(1)

    # All browsers failed — try without cookies (public video)
    print("  Could not read browser cookies — trying as public video...")
    result = subprocess.run(
        [yt_dlp_bin, "-f", "bestaudio/best", "-o", out_path, "--no-playlist", url],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        for f in Path(tmp_dir).glob("session.*"):
            return str(f)

    print(f"\n  Could not download video.")
    print(f"  Make sure you're logged into Facebook in Chrome or Safari.")
    print(f"  yt-dlp error: {result.stderr[-300:]}")
    sys.exit(1)


def _find_yt_dlp() -> str:
    for candidate in [
        "/Users/ashhub/Library/Python/3.9/bin/yt-dlp",
        "/usr/local/bin/yt-dlp",
        "/opt/homebrew/bin/yt-dlp",
        "yt-dlp",
    ]:
        if os.path.isfile(candidate) or shutil.which(candidate):
            return candidate
    print("  yt-dlp not found. Run: pip3 install yt-dlp")
    sys.exit(1)


# ── Step 2: Extract audio ─────────────────────────────────────────────────────
def extract_audio(input_path: str, tmp_dir: str) -> str:
    ext = Path(input_path).suffix.lower()
    if ext in [".mp3", ".m4a", ".wav", ".ogg", ".flac", ".webm"]:
        return input_path  # Already audio

    print(f"  Extracting audio from video...")
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    result = subprocess.run(
        [FFMPEG, "-i", input_path, "-vn", "-ar", "16000", "-ac", "1",
         "-b:a", "64k", audio_path, "-y", "-loglevel", "error"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr}")
        sys.exit(1)
    return audio_path


# ── Step 3: Get duration ──────────────────────────────────────────────────────
def get_duration(file_path: str) -> int:
    try:
        result = subprocess.run(
            [FFMPEG, "-i", file_path, "-f", "null", "-"],
            capture_output=True, text=True
        )
        for line in result.stderr.splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                return int(float(h) * 3600 + float(m) * 60 + float(s))
    except Exception:
        pass
    return 0


# ── Step 4: Transcribe ────────────────────────────────────────────────────────
def transcribe(audio_path: str) -> str:
    file_size = os.path.getsize(audio_path)
    size_mb = file_size / 1024 / 1024
    print(f"  Transcribing ({size_mb:.1f}MB)...")

    if GROQ_API_KEY:
        return _transcribe_groq(audio_path, file_size)
    elif OPENAI_API_KEY:
        return _transcribe_openai(audio_path, file_size)
    else:
        print("\n  No transcription API key found.")
        print("  Get a FREE Groq key at console.groq.com (2 min setup)")
        print("  Then add to .env.local:  GROQ_API_KEY=your_key_here")
        sys.exit(1)


def _transcribe_groq(audio_path: str, file_size: int) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    # Groq Whisper limit is 25MB — chunk if needed
    if file_size > 24 * 1024 * 1024:
        return _chunk_and_transcribe(audio_path, "groq", client)

    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=(Path(audio_path).name, f),
            model="whisper-large-v3",
            language="en",
            response_format="text"
        )
    return result if isinstance(result, str) else result.text


def _transcribe_openai(audio_path: str, file_size: int) -> str:
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    if file_size > 24 * 1024 * 1024:
        return _chunk_and_transcribe(audio_path, "openai", client)

    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1", file=f, language="en"
        )
    return result.text


def _chunk_and_transcribe(audio_path: str, provider: str, client) -> str:
    print("  File >25MB — splitting into 20-min segments...")
    tmp_dir = tempfile.mkdtemp()
    chunk_pattern = os.path.join(tmp_dir, "chunk_%03d.mp3")

    subprocess.run([
        FFMPEG, "-i", audio_path, "-f", "segment",
        "-segment_time", "1200", "-ar", "16000", "-ac", "1",
        "-b:a", "64k", chunk_pattern, "-y", "-loglevel", "error"
    ], check=True)

    chunks = sorted(Path(tmp_dir).glob("chunk_*.mp3"))
    transcripts = []
    for i, chunk in enumerate(chunks):
        print(f"  Transcribing chunk {i+1}/{len(chunks)}...")
        with open(chunk, "rb") as f:
            if provider == "groq":
                from groq import Groq
                result = client.audio.transcriptions.create(
                    file=(chunk.name, f),
                    model="whisper-large-v3",
                    language="en",
                    response_format="text"
                )
                transcripts.append(result if isinstance(result, str) else result.text)
            else:
                result = client.audio.transcriptions.create(
                    model="whisper-1", file=f, language="en"
                )
                transcripts.append(result.text)

    shutil.rmtree(tmp_dir)
    return " ".join(transcripts)


# ── Step 5: Categorize with Claude ───────────────────────────────────────────
def categorize(transcript: str, title_hint: str = "") -> dict:
    print("  Categorizing with Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are analyzing a sales training session transcript from Ashley Diep's "Breakfast Club" daily training.

Ashley is a real estate agent and sales coach. These sessions cover topics like working with sellers and buyers, handling objections, tonality, mindset, scripts, and closing techniques.

{"Session title hint: " + title_hint if title_hint else ""}

Analyze this transcript and return a JSON object with exactly these fields:

{{
  "title": "concise descriptive title (if not obvious from hint, derive from content)",
  "primary_category": "the single most dominant topic",
  "categories": ["array", "of", "all", "relevant", "categories"],
  "summary": "2-3 sentence summary of what was taught",
  "key_takeaways": [
    "specific, actionable takeaway 1",
    "specific, actionable takeaway 2",
    "up to 8 takeaways"
  ],
  "scripts": [
    "exact word-for-word script or phrase taught, if any",
    "another script"
  ],
  "objection_handling": [
    {{"objection": "the objection raised", "response": "the taught response"}},
    {{"objection": "...", "response": "..."}}
  ]
}}

Valid categories (use only these): {", ".join(VALID_CATEGORIES)}

Transcript:
{transcript[:12000]}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    text = message.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1:
        raise ValueError("Claude didn't return JSON")
    raw = text[start:end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Retry with explicit JSON escaping instruction
        print("  JSON parse failed, retrying with stricter prompt...")
        retry_prompt = prompt + "\n\nIMPORTANT: Your response must be valid JSON. Escape all apostrophes and quotes inside string values with a backslash. Do not use smart quotes. Return ONLY the JSON object, nothing else."
        msg2 = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": retry_prompt}]
        )
        text2 = msg2.content[0].text
        start2 = text2.find("{")
        end2 = text2.rfind("}") + 1
        return json.loads(text2[start2:end2])


# ── Step 6: Embed ─────────────────────────────────────────────────────────────
def embed(text: str) -> list:
    print("  Generating embedding...")
    client = voyageai.Client(api_key=VOYAGE_API_KEY)
    # Use summary + key takeaways for embedding (more signal-dense than full transcript)
    result = client.embed([text], model="voyage-3-large", input_type="document")
    return result.embeddings[0]


# ── Step 7: Insert into Supabase ──────────────────────────────────────────────
def insert_to_supabase(row: dict) -> None:
    print("  Inserting into Supabase...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/sales_training_sessions",
        headers=headers,
        json=row
    )
    if resp.status_code not in [200, 201]:
        print(f"  Supabase error {resp.status_code}: {resp.text}")
        sys.exit(1)
    inserted = resp.json()
    if inserted:
        print(f"  Saved with id={inserted[0].get('id')}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Process a Breakfast Club session")
    parser.add_argument("source", help="File path or Facebook URL")
    parser.add_argument("--date", default=str(date.today()), help="Session date (YYYY-MM-DD)")
    parser.add_argument("--title", default="", help="Optional title hint")
    args = parser.parse_args()

    source = args.source
    session_date = args.date
    title_hint = args.title

    print(f"\nBreakfast Club Pipeline")
    print(f"  Source : {source}")
    print(f"  Date   : {session_date}")
    print(f"  Title  : {title_hint or '(will be derived from content)'}\n")

    tmp_dir = tempfile.mkdtemp()
    try:
        # 1. Get the file
        is_url = source.startswith("http")
        if is_url:
            file_path = download_from_facebook(source, tmp_dir)
        else:
            file_path = os.path.expanduser(source)
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                sys.exit(1)

        # 2. Duration
        duration = get_duration(file_path)
        print(f"  Duration: {duration // 60}m {duration % 60}s")

        # 3. Extract audio
        audio_path = extract_audio(file_path, tmp_dir)

        # 4. Transcribe
        transcript = transcribe(audio_path)
        print(f"  Transcript: {len(transcript)} chars")

        # 5. Categorize
        analysis = categorize(transcript, title_hint)
        title = title_hint or analysis.get("title", f"Breakfast Club {session_date}")
        print(f"  Title: {title}")
        print(f"  Primary category: {analysis.get('primary_category')}")
        print(f"  Categories: {analysis.get('categories')}")

        # 6. Embed (summary + takeaways for dense signal)
        embed_text = analysis.get("summary", "") + " " + " ".join(analysis.get("key_takeaways", []))
        embedding = embed(embed_text)

        # 7. Insert
        row = {
            "session_date": session_date,
            "title": title,
            "source_url": source if is_url else None,
            "duration_seconds": duration,
            "categories": analysis.get("categories", []),
            "primary_category": analysis.get("primary_category"),
            "transcript": transcript,
            "summary": analysis.get("summary"),
            "key_takeaways": analysis.get("key_takeaways", []),
            "scripts": analysis.get("scripts", []),
            "objection_handling": analysis.get("objection_handling", []),
            "embedding": embedding,
        }
        insert_to_supabase(row)

        # 8. Move to processed (if local file in inbox)
        if not is_url and str(INBOX_DIR) in str(Path(file_path).resolve()):
            dest = PROCESSED_DIR / Path(file_path).name
            shutil.move(file_path, dest)
            print(f"  Moved to processed: {dest.name}")

        print(f"\nDone. '{title}' is now searchable in Supabase.\n")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
