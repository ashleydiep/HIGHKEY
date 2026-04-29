# Breakfast Club — Sales Training Pipeline

> Process, search, or review Breakfast Club sales training sessions.

## Usage

Run with optional arguments:
- `/breakfast-club` — show status and recent sessions
- `/breakfast-club search [topic]` — find training on a specific topic
- `/breakfast-club recent` — list the last 10 sessions stored

---

## What To Do

### If no arguments — show status

Query Supabase and report:
1. Total sessions stored in `sales_training_sessions`
2. Most recent session (date + title)
3. Sessions by category (count per primary_category)
4. Any date gaps in the last 30 days (missed sessions)

Use the Supabase REST API:
- URL: `https://aiwdgrrxfddaxfyahisc.supabase.co`
- Key: from `SUPABASE_SERVICE_ROLE_KEY` in `.env.local`

```
GET /rest/v1/sales_training_sessions?select=session_date,title,primary_category&order=session_date.desc&limit=10
```

### If `search [topic]`

Search for sessions relevant to the topic. Query:
```
GET /rest/v1/sales_training_sessions?select=session_date,title,primary_category,summary,key_takeaways,scripts,objection_handling&categories=cs.{"[category]"}
```

Or run semantic search via the `search_training` RPC function if an embedding can be generated.

Present results as:
- Session title + date
- Summary
- Key takeaways (bulleted)
- Word-for-word scripts (if any)
- Objection/response pairs (if any)

### If `recent`

List the last 10 sessions: date, title, primary category, duration.

---

## Adding a New Session (remind user of workflow)

If the user asks how to add a session or process a new video:

```
Daily workflow:
1. Download the Breakfast Club video (Video DownloadHelper Chrome extension → Facebook group)
2. Drop in ~/breakfast-club/inbox/
3. Run in terminal:
   bclub ~/breakfast-club/inbox/filename.mp4 --date YYYY-MM-DD

Or with a URL (if accessible):
   bclub "https://facebook.com/..." --date YYYY-MM-DD

Takes ~5-8 minutes. Transcript, takeaways, scripts, and objection handling
are all extracted automatically and stored in Supabase.
```

---

## Categories

Valid categories in the system:
`sellers`, `buyers`, `objection_handlers`, `tonality`, `mindset`, `scripts`, `concepts`, `closing`, `follow_up`, `roleplay`
