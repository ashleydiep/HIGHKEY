# /sync — Run All Data Syncs

Run all data sync scripts in sequence and report results.

## Steps

1. Run each script below using the Bash tool. Run them sequentially (each must finish before the next starts).
2. For each script, capture whether it succeeded or failed and the key output line (rows synced, error message, etc.).
3. After all scripts complete, print a clean summary table showing what synced and what (if anything) failed.

## Scripts to run (in order)

```bash
python3 scripts/sync/ghl.py
```
```bash
python3 scripts/sync/google_ads.py
```
```bash
python3 scripts/sync/google_ads_sheet.py
```
```bash
python3 scripts/sync/gmail.py
```
```bash
python3 scripts/sync/meta.py
```
```bash
python3 scripts/sync/facebook_ads.py
```
```bash
python3 scripts/sync/youtube.py
```

## Output format

After all scripts finish, show:

```
Sync complete — [timestamp]

| Source          | Status  | Result                  |
|-----------------|---------|-------------------------|
| GHL             | ✅ Done  | 1,434 contacts synced   |
| Google Ads      | ✅ Done  | 154 rows synced         |
| Google Ads Sheet| ✅ Done  | 3 months synced         |
| Gmail           | ✅ Done  | 4,140 emails synced     |
```

If any script fails, show the error clearly and continue with the rest. Do not stop on failure.
