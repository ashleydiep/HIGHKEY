# /week — Weekly Targets

> Auto-generate this week's KPI targets based on your year-end goals and recent actuals. Review and tweak before saving.

## Usage
- `/week` — generate targets for this week (or show existing ones)
- `/week force` — regenerate from scratch even if targets already exist

---

## Instructions

### If argument is "force" or no targets file exists for this week:

Run the generator:
```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 scripts/weekly_targets.py
```

The script will:
1. Pull YTD actuals + last week's numbers from Supabase
2. Pull the Agent GHL pipeline
3. Generate targets with Claude based on year-end goals
4. Print the targets and wait for input

**After the script prints the targets**, ask the user:
> "Want to tweak anything? Tell me what to change (e.g. 'make agent contacts 30, bump seller appts set to 15') or say 'looks good' to save."

If they want changes, apply them by re-running with `--force` or calling `scripts/weekly_targets.py` with their adjustments piped in. Alternatively, load the generated JSON from `data/weekly-targets/YYYY-Www.json`, apply their edits directly, and save.

### If targets already exist for this week:

Run:
```bash
cd /Users/ashhub/Desktop/HIGHKEY/proagent-os && python3 scripts/weekly_targets.py
```

Show the existing targets and ask: "Want to adjust anything, or are these still good?"

If they want changes:
1. Load `data/weekly-targets/{WEEK_KEY}.json`
2. Apply their requested changes
3. Save the updated file

---

## After saving

Confirm: "Targets set for [week]. Your daily brief will now show your progress vs these each day."

Remind: "Run `/week` again any time to review or adjust."
