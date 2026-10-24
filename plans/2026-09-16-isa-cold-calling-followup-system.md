# ISA Cold-Calling Follow-Up System

**Context:** HKS Paid Ads track paused Sept 16, 2026 (resuming 2027) — ISA hire is the cheaper lead-volume play for now. This is the follow-up infrastructure needed so a sales ISA can cold call for PROAGENT without leads leaking or appointments no-showing.

---

## 1. Lead Sourcing & CRM Entry

- ISA pulls from existing sources: expired listings, FSBO, circle prospecting off Just Listed/Just Sold (ARK Agent via Mojo) — same sources already documented in `context/strategy.md`.
- Every dial logged in Mojo at time of call, not batched at end of day — batching is where lead data quality dies.
- Any lead with email + real motivation gets transferred to GHL same day (existing Lead Transfer Process) and added to FB retargeting.

## 2. Call Disposition Taxonomy → Auto-Triggered Next Action

Extend the existing tag set (Not interested / Follow-up / Appointment set / niche tags / Need / Skip tracing) so every disposition has a defined next step — no disposition should be a dead end:

| Disposition | Next Action | Owner | Timing |
|---|---|---|---|
| Appointment set | Handoff to Ashley (see §3) | ISA | Immediate |
| NOW (motivated, <1wk) | Same-day callback attempt #2 | ISA | Same day |
| HOT (<1mo) | Weekly call + nurture email | ISA | Ongoing |
| WARM (1-6mo) | Bi-weekly call | ISA | Ongoing |
| COLD (vague/long timeline) | Add to newsletter drip, quarterly touch | ISA → GHL automation | Ongoing |
| Not interested | Mark dead, no further dials | ISA | — |
| No answer (1st-3rd attempt) | Redial per double-dial cadence | ISA | Next business day |
| Skip tracing needed | Flag for data cleanup, redial once resolved | ISA | Within 48h |

## 3. Appointment Handoff Protocol (this is the critical failure point)

- The moment an ISA books an appointment, they text/Slack Ashley immediately — not end of day. This mirrors the existing "Immediate Follow-Up within 5 minutes" rule for booked seller appointments; the ISA is now the trigger for that clock, not Ashley.
- Handoff message includes: seller name/number, address, motivation, rough timeline, asking price if known, appointment date/time.
- Ashley (or whoever owns it) sends the intro text + personalized video + email within 5 minutes of handoff, per the existing Follow-Up Process.

## 4. Appointment Confirmation Ownership

- "Confirm every appt 24h before" is already a weekly non-negotiable — assign this explicitly to the ISA as part of their role, not left ambiguous. Unconfirmed appointments are the direct cause of a bad show rate, and show rate is the actual lever between appts set (5 this week) and appts attended (unreported this week — worth checking why).
- Confirmation call/text logged in Mojo/GHL same as an initial dial.

## 5. Script & Objection Handling (blocking dependency)

- Current asset list status: cold call scripts marked "partial." An ISA cannot cold call effectively off a partial script — this needs to be finished and written down before/during onboarding, not learned informally by listening to Ashley's calls.
- Structure: pain point → motivation → solution (existing framework), plus a written objection-handling doc covering the standard seller objections (price, timing, "just looking," using another agent, etc.) with the actual rebuttal Ashley uses.

## 6. Reporting Cadence

- ISA reports daily: contacts, appts set, dispositions logged. Feeds directly into the existing weekly scorecard system (`outputs/scorecards/`) — no new reporting tool needed, just plug ISA numbers into the same PROAGENT contacts/appts-set rows.
- Friday check-in stays as-is: Contacts | Appts set | Attended | Listings | Closings, per `data/goals/90-day-weekly-plan.md`.

## 7. QA

- Weekly spot-check of 3-5 recorded calls for script adherence, tone, and correct disposition tagging (mis-tagged leads silently break the follow-up cadence above).

## 8. Compensation Alignment

- Tie incentive to appts **set and shown**, not raw dial count — dial count alone doesn't fix the actual bottleneck (contact volume already improved this week: 100 contacts → 5 appts, roughly a 20:1 ratio, close to the stated 24-30:1 norm). The system should reward the behaviors that move show rate, since that's the gap between appts set and revenue.

## 9. Ramp Plan

- Week 1-2: shadow Ashley's calls, drill script and objections, no live dials.
- Week 3: live dials with Ashley reviewing first 10 dispositions/day.
- Week 4+: full autonomy with weekly QA spot-checks (§7).

---

## 10. KPI Tracking — Staying on Top of the ISA

Two layers: **daily** (catch a bad day before it becomes a bad week) and **weekly** (the actual performance read).

### Daily (ISA self-reports, takes 2 min)

| KPI | Why it matters |
|---|---|
| Dials made | Leading indicator — if this drops, everything downstream drops |
| Contacts (live conversations) | Dials ≠ contacts; a dial spike with flat contacts means bad calling hours or bad list quality |
| Appts set | The number that actually matters |
| Dispositions logged / contacts made | Should be ~100% — gaps here mean the follow-up cadence in §2 is silently breaking |

### Weekly (feeds the existing scorecard, reviewed same Friday cadence as PROAGENT numbers)

| KPI | Target | Red Flag |
|---|---|---|
| Contacts | 60+ (same PROAGENT floor) | Two weeks below floor → re-check calling hours/list quality before assuming ISA effort |
| Contacts → Appts set ratio | 24-30 : 1 | Ratio much worse than 30:1 → script/qualification problem, not volume problem |
| Appts set → Appts attended (show rate) | 65%+ (2 of 3 per existing target) | Below this → §4 confirmation step is being skipped, not a lead-quality issue |
| Handoff SLA (§3) | 100% within 5 min | Any miss → direct revenue leak, flag same day, don't wait for Friday |
| Disposition tagging accuracy (from §7 QA spot-check) | 100% correctly tagged | Errors compound silently into the wrong nurture cadence |

### Monthly

- Contacts-to-listing conversion, fully loaded cost per listing (ISA pay ÷ listings sourced) — this is the number that validates "ISA is cheaper than ads." Compare against what a paid-ads CPL/CPA would have cost (Track 1 metrics in `context/strategy.md`, paused but still the benchmark).

**Where this lives:** daily numbers go in a running log (new sheet or GHL note), weekly numbers slot into the existing `outputs/scorecards/` file alongside PROAGENT's own numbers — same Friday check-in, ISA is just another row, not a separate system.

---

## 11. Duplicability — Making This Translate to ISA #2, #3...

This system was already meant to be duplicable per your own note in `companies.md` ("this process should be duplicable for any ISA or agent added to the team"). What makes §1-10 actually transfer to a second hire, rather than living in ISA #1's head:

- **Nothing above can be person-specific.** The script (§5), disposition taxonomy (§2), and handoff protocol (§3) must be written as standalone documents an ISA reads and follows — not things ISA #1 learned by shadowing Ashley informally. If ISA #1 leaves, ISA #2 should onboard from the doc, not from ISA #1's notes or memory.
- **Ramp plan (§9) is the onboarding SOP, verbatim, for every new hire** — same 4 weeks, same shadow → supervised → autonomous structure, no re-inventing it per person.
- **KPI targets (§10) stay fixed benchmarks, not tuned to one person's baseline.** Track each ISA's numbers as their own row against the same fixed targets (60+ contacts, 24-30:1 ratio, 65%+ show rate) — this is what lets you compare ISA #1 vs ISA #2 apples-to-apples and spot underperformance fast instead of assuming "that's just how ISA #2 works."
- **Lead assignment must be explicit once there are 2+ ISAs.** Decide now (before hire #2) whether leads are split by list/territory or round-robin in Mojo/GHL — without this, two ISAs will double-dial the same lead, which burns the lead and makes disposition tagging (§2) unreliable.
- **CRM structure stays role-based, not person-based.** Pipelines, tags, and saved views in Mojo/GHL should be set up for "the ISA role," not named after ISA #1 — so adding a second seat is a permissions change, not a rebuild.
- **Compensation formula (§8) is a fixed formula, not negotiated per hire** — tie to appts set/shown for everyone so the incentive structure doesn't have to be redesigned each time you scale the team.

**Practical output:** the deliverables in §5 (script + objections) and §9 (ramp plan) should be written as a single onboarding packet — that packet *is* the duplicability mechanism. Build it once for ISA #1, hand the same packet to ISA #2.

---

## 12. Daily Expectations & Non-Negotiables

What to set day one, in writing, as part of the onboarding packet (§11) — not communicated informally and re-explained every week.

**Schedule (as set):**
- Breakfast Club attendance and participation daily (confirm CT vs. PT — Breakfast Club is documented elsewhere as 9:30-10:00 AM **CT**; if the ISA is in a different time zone, write down the actual local time they need to log on, not just "9:30," so it's unambiguous)
- On calls together during the day — joint call blocks, not solo unsupervised dialing during the ramp period (ties to §9 Ramp Plan)
- Nightly: ISA flags their longest conversations for Ashley to review — good instinct, this is real-time QA instead of waiting for the weekly spot-check in §7

**Add to this list:**
- **Daily quota, stated as a number, not a vibe** — minimum dials/contacts expected per day (ties to §10 daily KPI table), so "did you have a good day" isn't a judgment call either of you has to make from memory
- **Disposition logging is same-day, not end-of-week** — every call tagged in Mojo before moving to the next, per §2; this is the rule most likely to quietly slip without being stated explicitly
- **Appointment handoff SLA** — text/Slack Ashley within 5 minutes of booking, per §3, stated as a hard rule with a consequence for misses (this is a direct revenue leak if skipped)
- **Response time during work hours** — how fast the ISA should reply to Ashley's messages, and vice versa, so neither side assumes availability
- **What "success" looks like numerically by week 4** — tie directly to the ramp plan (§9) and KPI targets (§10): contact floor, show rate, ratio — so the ISA knows the bar, not just "I'll know it when I see it"
- **Call recording consent/compliance** — if calls are recorded for QA (§7), the ISA (and the policy for leads) should know that upfront
- **Equipment/environment baseline** — reliable internet, headset, quiet space during call blocks — unglamorous but a common reason dials quietly drop
- **What happens if quota is missed** — define this before it happens (coaching conversation vs. a hard consequence), so it's a known process instead of an improvised one in the moment
- **Lead/data ownership** — leads, scripts, and call recordings belong to the business, not the individual ISA; worth stating plainly, especially once a second ISA is hired and lead assignment (§11) matters

---

**Open dependency:** §5 (finished script + objection doc) blocks a real onboarding date — worth prioritizing that write-up before sourcing candidates.
