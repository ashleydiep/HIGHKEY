# Audit System — Check Your AI OS Against Current Best Practices

> Run this anytime to check whether your AI OS is following current Claude Code best practices, or if the ecosystem has moved on and you need to update.

## Purpose

Claude Code evolves quickly. What was current at setup may be superseded in weeks. This audit reads your project files, compares them against a checklist of current patterns, and reports what's up to date (✅), what's outdated (⚠️), or what's missing (❌).

Run this monthly, or whenever you suspect you've drifted from best practice.

---

## Phase 1: Read the Project

Read the following files to understand the current setup:

1. `CLAUDE.md` — architecture and model IDs
2. `context/` — all files in this directory
3. `.claude/commands/` — all skills in this directory
4. `.mcp.json` — MCP server configuration (if it exists)
5. `reference/` — all reference docs in this directory
6. Check for: `.claude/rules/`, `data/decisions/`, `~/.claude/projects/<project>/memory/` (Auto Memory)

---

## Phase 2: Audit Checklist

For each item below, report one of: ✅ (current), ⚠️ (outdated, needs update), ❌ (missing, should add), ➖ (not applicable).

### Core Setup

- [ ] `CLAUDE.md` exists
- [ ] Project has a `context/` directory with business-specific subdirectories (companies, strategy, team, current-data, etc.)
- [ ] Project has a `.claude/commands/` directory with at least the core skills (`/prime`, `/build-context`, `/decide`, `/create-plan`, `/implement`)

### Model IDs (last verified April 2026)

- [ ] Latest Opus referenced is `claude-opus-4-7` (not 4-6 or earlier)
- [ ] Sonnet referenced is `claude-sonnet-4-6` (not 4-5 or earlier)
- [ ] Haiku referenced is `claude-haiku-4-5-20251001` or later (Haiku 3 retired 19 April 2026)
- [ ] No deprecated model IDs present (no `claude-3-*`, no `claude-opus-4-20250514`, no `claude-3-haiku-20240307`)

### Learning & Memory

- [ ] `CLAUDE.md` documents the three learning layers: CLAUDE.md (declarative rules), Auto Memory (observed patterns), Decision Engine (structured decision logging)
- [ ] Auto Memory directory exists at `~/.claude/projects/<project>/memory/` (enabled by default in current Claude Code)
- [ ] Decision Engine is implemented — `data/decisions/` directory exists with at least one logged decision
- [ ] Decision logs include "expected vs actual outcome" fields

### Scheduling & Automation

- [ ] References to **Routines** (not "Cloud Scheduled Tasks" — that term was retired April 2026)
- [ ] If scheduled automation is set up, it uses Routines at https://claude.ai/code/routines
- [ ] If using local scheduling, it's in `reference/scheduling.md`

### Mobile & Channels

- [ ] Mobile access is configured in at least one path: Slack bot (managed connector + Routine), Telegram bot (serverless webhook), or Claude mobile app (Remote Control / Web)
- [ ] If using Telegram: pattern is serverless webhook (not Python script on a VPS — that pattern is retired)
- [ ] Claude mobile app is installed for on-the-go full Claude Code access

### Services & Connectors

- [ ] Managed connectors on claude.ai are used for: Notion, Gmail, Google Drive, Google Calendar, Slack (when the member uses any of these)
- [ ] Manual MCP (`.mcp.json`) is used for everything else
- [ ] Database choice is appropriate: Files API + Claude embeddings (for first AI OS, <500 docs) OR Supabase + pgvector (for scaling, multi-user, or sellable systems)
- [ ] MCP services are verified against the MCP Registry (https://code.claude.com/docs/en/mcp) at setup — not based on a static list

### Advanced Features (optional, month 2+)

- [ ] Custom skills exist in `.claude/commands/` (shortcuts for repeated workflows)
- [ ] Hooks are configured if lifecycle automation is valuable (e.g., auto-prime on session start)
- [ ] Subagents are used if work is split across focused sub-tasks
- [ ] `.claude/rules/` directory exists if `CLAUDE.md` exceeds 200 lines (path-scoped rules reduce context bloat)

### Documentation Hygiene

- [ ] `context/strategy.md` date/quarter example is current (not stuck on an old quarter)
- [ ] No stray references to "Codex" (should be "Claude Code")
- [ ] No references to features that were renamed or deprecated

---

## Phase 3: Report

Produce a concise report with three sections:

### 1. Current ✅
List items that pass the audit. Brief — just confirm the member is up to date.

### 2. Outdated ⚠️
For each outdated item: what the old pattern is, what the current April 2026 pattern is, and one line on how to migrate. Example:

> ⚠️ `reference/scheduling.md` uses the term "Cloud Scheduled Tasks." 
> **Current term:** "Routines" (as of April 2026). 
> **To fix:** Rename throughout `reference/scheduling.md`. See https://code.claude.com/docs/en/routines.md.

### 3. Missing ❌
For each missing item: what it is, why it matters, how to add it. Example:

> ❌ No Auto Memory documented in CLAUDE.md. 
> **What it is:** Claude's platform-level learning feature, enabled by default. 
> **Why it matters:** Auto Memory captures observed patterns and preferences; complements your Decision Engine. 
> **To add:** Document it in CLAUDE.md alongside the Decision Engine. Run a session — Claude creates `~/.claude/projects/<project>/memory/` entries automatically.

---

## Phase 4: Update the System

For any ⚠️ or ❌ items the member wants to address:

1. Offer to make the fix now (show the diff, apply it with their approval)
2. For structural changes (e.g., adding Auto Memory awareness to CLAUDE.md), draft the update and show it for review
3. For infrastructure changes (e.g., migrating from a VPS Telegram bot to serverless), create a plan in `plans/` via `/create-plan`

Do NOT make changes without approval. This audit surfaces; the member decides.

---

## Keeping This Audit Current

The checklist above reflects **April 2026** best practices. Claude Code ships new features continuously. If you notice a new Anthropic feature that should be audited, update this skill to include it.

Recent feature shifts to watch:
- **Routines** (replaces Cloud Scheduled Tasks — Q1 2026)
- **Remote Control** (replaces the old Channels research preview pattern — Q1 2026)
- **Managed connectors** (Notion, Gmail, Drive, Calendar, Slack — 2025-2026)
- **Auto Memory** (enabled by default — 2026)
- **Claude Code on the Web** (cloud sessions — 2026)
- **Skills / Hooks / Subagents** (intermediate-level features — 2026)

Check https://code.claude.com/docs/en for the latest, and update this audit accordingly.

---

_Your AI OS only works if it stays current. Run this audit monthly. Five minutes here saves hours of drift later._
