# /brief — Daily Brief

> Generate today's morning intelligence report from live Supabase data.

## What It Does

Runs `scripts/daily_brief.py` which pulls:
- GHL open opportunities by pipeline and stage
- Yesterday's KPI numbers from `daily_kpis`
- MTD totals and key ratios
- Latest Breakfast Club session takeaways

Then generates a structured brief with Claude Opus and saves it to `outputs/briefs/YYYY-MM-DD.md`.

---

## Instructions

Run the script:

```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 scripts/daily_brief.py
```

Display the output to the user exactly as generated.

Report where the file was saved: `outputs/briefs/{TODAY}.md`

---

## If the script fails

- **Missing module**: run `pip3 install anthropic requests` then retry
- **Supabase error**: check that `.env.local` has `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- **No KPI data for yesterday**: normal if `/numbers` wasn't run — brief will note it and continue
- **No Breakfast Club data**: normal if no sessions are loaded yet — brief skips that section

---

## Tip

Run `/numbers` at end of day to log your numbers, then `/brief` next morning to see them in context.
