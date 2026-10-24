# Follow-Up Sequences v2 — GHL Ready
## Cancelled Appointments + Post-Meeting No-Lists
**Built:** July 30, 2026 | **Load into:** GHL Workflows

---

## HOW TO USE THIS IN GHL

### Setup Steps
1. Create a **custom field** on the contact: `Motivation` (dropdown)
2. Create a **custom field**: `Survey Completed` (yes/no checkbox)
3. When tagging a contact for either sequence, fill in their Motivation before triggering the workflow
4. Each message with `{motivation_line_X}` uses a **conditional branch** in GHL — see the **Motivation Variants Table** at the bottom of this doc
5. `{motivation_line_A}` = Phase 1 line | `{motivation_line_B}` = Phase 2 line | `{motivation_line_C}` = Phase 3 early | `{motivation_line_D}` = Phase 3 late

### Survey Branch
At Day 0: Add a GHL condition — `IF Survey Completed = Yes → skip to Day 14 branch`
This avoids repeating content they've already received.

### Kill Switch
Add to every workflow: `IF Contact Stage = Active Client OR Listing Taken → Remove from sequence`

---

## SEQUENCE 1: CANCELLED APPOINTMENT

**Trigger tag:** `Cancelled Appt`
**Goal:** Re-engage → reset the appointment → stay visible until they're ready

---

### ── PHASE 1: RE-ENGAGEMENT BURST (Days 1–7) ──

---

**DAY 0 — Text (send within 2 hours of missed appt)**

> Hey {first_name} — Ashley here. Looks like we missed each other today — no worries at all. {motivation_line_A} I had some solid numbers pulled for your area. What does your schedule look like this week to connect?

---

**DAY 1 — Text (morning)**

> Morning {first_name} — Ashley here. Circling back from yesterday. I still have those numbers for [their area] ready — takes about 10 minutes and gives you a real picture of what your home is worth right now. Want to grab a time today or tomorrow?

---

**DAY 3 — Text (value add)**

> Hey {first_name} — quick market note: homes in [their area] are averaging [X] days on market this month. {motivation_line_A} Happy to show you exactly where yours would land — no commitment needed. Want me to pull it?

---

**DAY 5 — Text (soft ask)**

> Hey {first_name} — Ashley here. I don't want to keep bugging you, so I'll keep this short. Is this still something you're thinking about, or has the timing shifted? Either answer is fine — just want to make sure I'm not reaching out if plans have changed.

---

**DAY 7 — Email**

**Subject:** What's happening in [their area] right now — thought you'd want to see this

> Hi {first_name},
>
> I know we weren't able to connect last week. Instead of just another "checking in" message, I wanted to send something actually useful.
>
> Here's a quick snapshot of [their area] right now:
> - Average days on market: [X]
> - Recent solds nearby: [2–3 real comps — address, price, DOM]
> - What this means for your home: [honest 1-sentence take]
>
> {motivation_line_A}
>
> I'm not going anywhere. When the timing is right, I'd love to finally connect and show you what I put together for your home specifically.
>
> — Ashley
> [number]

---

### ── PHASE 2: WEEKLY VALUE TOUCHES (Days 8–30) ──

---

**DAY 10 — Text**

> Hey {first_name} — Ashley here. {motivation_line_B} No pressure — just want to make sure you have the right info when you're ready to make a move. Here if you need me.

---

**DAY 14 — Email (→ INSERT TESTIMONIAL FROM SURVEY SEQUENCE HERE)**

**Subject:** A seller in [their area] just closed — here's what happened

> Hi {first_name},
>
> Wanted to share something from this month.
>
> [INSERT TESTIMONIAL — pull from your home evaluation survey sequence. Use one that's closest to their situation — vacant seller, upsizer, or area-specific.]
>
> *"[Exact client quote — the more specific the better]"* — [First name, area]
>
> {motivation_line_B}
>
> What they went through is probably not that different from where you are. If you want to talk through what this could look like for your home, I'm a text away.
>
> — Ashley

---

**DAY 21 — Text**

> Hey {first_name} — Ashley Diep. {motivation_line_B} Wanted to check in — still thinking about making a move, or has the plan shifted? No pressure either way.

---

**DAY 28 — Email**

**Subject:** [Their area] — what sold this month

> Hi {first_name},
>
> Quick monthly update for [their area]:
>
> [3–4 bullet points: avg sale price, DOM, notable solds, any market shift]
>
> {motivation_line_B}
>
> The data is here if you want to use it. Whenever you're ready to have that conversation — I'm here.
>
> — Ashley

---

### ── PHASE 3: LONG-BURN MONTHLY TOUCHES (Days 31–180) ──

---

**DAY 45 — Text**

> Hey {first_name} — Ashley here. {motivation_line_C} Still thinking about the move? Happy to connect whenever the timing makes sense.

---

**DAY 60 — Email (→ INSERT SECOND TESTIMONIAL HERE)**

**Subject:** Just closed: [brief property description]

> Hi {first_name},
>
> Another one to share —
>
> [INSERT SECOND TESTIMONIAL from survey sequence — ideally a different situation/story from the Day 14 one]
>
> *"[Exact quote]"* — [First name, area]
>
> {motivation_line_C}
>
> When you're ready to have that 10-minute conversation, I'll be here.
>
> — Ashley

---

**DAY 75 — Text**

> Hey {first_name} — {motivation_line_C} Just checking in — any update on where things stand for you?

---

**DAY 90 — Email (Quarterly Market Report)**

**Subject:** [Their area] — Q[X] 2026 market update

> Hi {first_name},
>
> Quarterly snapshot for [their area]:
>
> - Avg days on market: [X] (vs [X] last quarter)
> - Median sale price: $[X] (up/down [X]%)
> - Inventory: [low/normal/high]
> - Buyer demand: [hot/steady/softening]
>
> Bottom line: [1 honest sentence on what this means for a seller right now]
>
> {motivation_line_C}
>
> If you're still thinking about selling in the next 3–6 months — now is a good time to start mapping out the plan, even if you're not ready to list yet.
>
> — Ashley
> [number]

---

**DAY 110 — Text**

> Hey {first_name} — Ashley here. {motivation_line_D} Still here when the timing is right.

---

**DAY 130 — Email**

**Subject:** Something shifted in [their area] — thought you should know

> Hi {first_name},
>
> [Relevant market change — interest rate shift, inventory change, new comps, seasonal trend.]
>
> {motivation_line_D}
>
> Depending on where you are in the decision, this might be worth factoring in. Happy to break it down for your specific situation.
>
> — Ashley

---

**DAY 150 — Text**

> Hey {first_name} — {motivation_line_D} It's been a few months. Are you still planning on making a move, or has the plan changed completely? Either answer is fine — just want to make sure I'm reaching out for a reason.

---

**DAY 165 — Email (→ INSERT THIRD TESTIMONIAL HERE)**

**Subject:** Still thinking of you — one more story worth sharing

> Hi {first_name},
>
> I know it's been a while. I wanted to share one more story before I close the loop.
>
> [INSERT THIRD TESTIMONIAL — ideally the strongest one you have. The 2-year listing or the 3-attempt close story works perfectly here.]
>
> {motivation_line_D}
>
> I share this because most people in your situation eventually do sell — the question is just timing and who they work with when they do.
>
> I'll still be here.
>
> — Ashley

---

**DAY 180 — Text + Email (Close the Loop)**

**Text:**
> Hey {first_name} — Ashley Diep. It's been about 6 months since we were supposed to connect. {motivation_line_D} Are you still thinking about the move, or has life taken a different direction? No hard feelings either way — just want to close the loop.

**Email:**
**Subject:** 6 months — still here if you need me

> Hi {first_name},
>
> It's been about 6 months since we had that appointment on the books.
>
> {motivation_line_D}
>
> If the timing still isn't right — completely understood. If things have shifted and selling is back on the table — I'm still the same person, and I'd still love to help.
>
> If you'd like me to stop reaching out, just reply and I'll remove you from my list. No hard feelings.
>
> Otherwise — I'll be here.
>
> — Ashley
> [number] | [email]

---
---

## SEQUENCE 2: POST-APPOINTMENT — DECIDED NOT TO LIST

**Trigger tag:** `Met — Did Not List`
**Goal:** Stay top of mind without pressure. Be the second call when their agent fails or when they're ready.
**Key difference from Sequence 1:** They met with you face-to-face. The tone is warmer, more personal, zero agenda.

---

### ── PHASE 1: RE-ENGAGEMENT BURST (Days 1–7) ──

---

**DAY 0 — Text (same day, within 2 hours of meeting)**

> Hey {first_name} — Ashley here. Really enjoyed meeting with you today. {motivation_line_A} Whatever you decide — I'm rooting for you. If you have any questions as you're thinking it through, I'm always just a text away.

---

**DAY 1 — Email (Thank you + leave one useful thing)**

**Subject:** Great meeting you today — one thing I wanted to leave you with

> Hi {first_name},
>
> Thank you for taking the time to sit down with me today. I know choosing an agent is a big decision and I appreciate you giving me the chance.
>
> I want to leave you with one thing from our conversation:
>
> [INSERT SPECIFIC NOTE FROM THE APPOINTMENT — the comp that surprised them, the pricing insight you shared, the DOM stat for their street. The more specific, the better. This should feel like you were paying attention.]
>
> {motivation_line_A}
>
> No strings attached — just want you to have good information going into this, regardless of who you work with.
>
> If anything comes up, you know where to find me.
>
> — Ashley
> [number]

---

**DAY 3 — Text (value, no agenda)**

> Hey {first_name} — Ashley here. Wanted to pass along a quick note: [a relevant market update for their area — a recent sale nearby, a DOM shift, something real and specific]. Thought you'd want to know as you're thinking through the decision. No agenda — just keeping you informed.

---

**DAY 7 — Email**

**Subject:** Quick market update for [their area]

> Hi {first_name},
>
> {motivation_line_A}
>
> Quick snapshot of what's happening in [their area] this week:
> - [Recent nearby sold + price + DOM]
> - [Any notable market movement]
>
> Just want to make sure you have current data as you're making your decision — whoever you end up working with.
>
> — Ashley

---

### ── PHASE 2: WEEKLY VALUE TOUCHES (Days 8–30) ──

---

**DAY 10 — Text**

> Hey {first_name} — Ashley here. Hope things are going smoothly. {motivation_line_B} Happy to be a resource even if you're working with someone else — no agenda.

---

**DAY 14 — Email (→ INSERT TESTIMONIAL FROM SURVEY SEQUENCE)**

**Subject:** A seller in a similar situation — thought this might resonate

> Hi {first_name},
>
> I was thinking about our conversation and wanted to share something.
>
> [INSERT TESTIMONIAL — match it as closely as possible to their situation. If they're an upsizer, use an upsizer story. If their home was on the market before, use the 3-attempt close story.]
>
> *"[Exact quote]"* — [First name, area]
>
> {motivation_line_B}
>
> Not sharing this to second-guess anything — just thought it might be useful context.
>
> — Ashley

---

**DAY 21 — Text**

> Hey {first_name} — Ashley Diep. {motivation_line_B} How's everything going? Not looking for business — genuinely just curious how it's going for you.

---

**DAY 28 — Email (Monthly Market Update)**

**Subject:** [Their area] — what happened this month

> Hi {first_name},
>
> Monthly numbers for [their area]:
>
> [3–4 honest bullets: avg sale price, DOM, any notable shifts]
>
> {motivation_line_B}
>
> Just keeping you in the loop — these numbers are useful regardless of where you are in the process.
>
> Hope your sale is moving in the right direction.
>
> — Ashley

---

### ── PHASE 3: LONG-BURN MONTHLY TOUCHES (Days 31–180) ──

---

**DAY 45 — Text (Best conversion opportunity)**

> Hey {first_name} — Ashley here. {motivation_line_C} Checking in — how's everything going with the sale? Not looking for anything — genuinely just want to know how it's going for you.

*→ GHL note: If they respond negatively here (struggling, stalled, agent isn't performing) — this is the moment. Flag for immediate personal follow-up call.*

---

**DAY 60 — Email (→ INSERT SECOND TESTIMONIAL)**

**Subject:** Just closed — thought of you

> Hi {first_name},
>
> Just wrapped up a sale I wanted to share.
>
> [INSERT SECOND TESTIMONIAL — different from Day 14. Use the 2-year listing story or the 3-attempt close here — powerful proof that problems get solved.]
>
> {motivation_line_C}
>
> I share this because when we met, you mentioned [reference their specific situation from appointment notes]. This seller wasn't that different from where you were.
>
> Still rooting for you.
>
> — Ashley

---

**DAY 75 — Text**

> Hey {first_name} — {motivation_line_C} Thinking about you — hope things are moving in the right direction.

---

**DAY 90 — Text (Direct, respectful)**

> Hey {first_name} — it's been about 3 months since we met. {motivation_line_C} How did everything go with the sale? If it worked out — amazing. If you're still navigating it — I'm here, no awkwardness.

---

**DAY 110 — Email**

**Subject:** Something changed in the market — worth knowing

> Hi {first_name},
>
> [Relevant market development for their area.]
>
> {motivation_line_D}
>
> Depending on where things stand for you, this could be worth factoring in. Happy to chat if useful.
>
> — Ashley

---

**DAY 130 — Text**

> Hey {first_name} — Ashley here. {motivation_line_D} Just checking in — if you ever want a second set of eyes on anything, I'm always happy to help. No agenda.

---

**DAY 150 — Email (→ INSERT THIRD TESTIMONIAL — your strongest one)**

**Subject:** Still thinking about you — one more story

> Hi {first_name},
>
> It's been a few months since we sat down together. I wanted to share one more story before I close the loop.
>
> [INSERT STRONGEST TESTIMONIAL — the 2-year listing, the 3-attempt close, or your most dramatic result. This is the last proof point before Day 180.]
>
> *"[Exact quote]"* — [First name, area]
>
> {motivation_line_D}
>
> Most people I meet with eventually do sell. The question is always just timing. I'll still be here when yours is right.
>
> — Ashley

---

**DAY 180 — Text + Email (Close the Loop)**

**Text:**
> Hey {first_name} — Ashley Diep. It's been about 6 months since we met. {motivation_line_D} Hope everything worked out. If it did — amazing. If you're still figuring it out — I'm still here. No pressure.

**Email:**
**Subject:** 6 months later — still here if you need me

> Hi {first_name},
>
> It's been about 6 months since we sat down together.
>
> {motivation_line_D}
>
> If everything went as planned — I genuinely hope your next chapter is everything you wanted.
>
> If things didn't quite land the way you hoped — whether the sale stalled, the market shifted, or plans changed — I'm still the same person you met. No awkwardness, no "I told you so." Just a conversation about what's next.
>
> If you'd like me to stop reaching out, just reply and I'll take you off my list. No hard feelings.
>
> Otherwise — I'm here.
>
> — Ashley
> [number] | [email]

---
---

## MOTIVATION VARIANTS TABLE

> **How to use in GHL:** For each message containing `{motivation_line_X}`, create a conditional branch for each motivation type and swap in the corresponding line below.

---

### UPSIZING
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"I know you're looking to make a move into something bigger — getting the timing right on the sale side makes everything else easier."* |
| B (Days 8–30) | *"Upsizers who wait too long often find themselves buying at the top of the next cycle. Getting your sale locked first puts you in a much stronger position."* |
| C (Days 31–90) | *"The goal hasn't changed — getting you into that next home. The sale is the first domino."* |
| D (Days 91–180) | *"Every month you're waiting to upsize is a month you're not in the home you actually want."* |

---

### DOWNSIZING
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"I know you're looking to simplify — getting the right number on your sale makes that next chapter a lot easier to step into."* |
| B (Days 8–30) | *"Downsizing at the right time means walking away with maximum equity. Waiting for 'perfect' usually costs more than it saves."* |
| C (Days 31–90) | *"The freedom you're looking for on the other side of this sale is real — the sale is the only thing standing between you and it."* |
| D (Days 91–180) | *"Simplifying your life starts with one decision. When you're ready to make it — I'm here."* |

---

### RELOCATION
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"With a move out of the area on the horizon, getting your sale handled fast and clean is everything — you don't want this dragging while you're trying to settle somewhere new."* |
| B (Days 8–30) | *"Relocations have a deadline built in — which is actually an advantage when it comes to pricing and positioning your home."* |
| C (Days 31–90) | *"The longer your Houston home sits, the harder it is to focus on your next chapter. Getting this handled cleanly is the priority."* |
| D (Days 91–180) | *"Whether the move already happened or it's still coming — this sale matters. I know how to move these fast."* |

---

### DIVORCE / LIFE CHANGE
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"I know this is a sensitive time. Getting this handled cleanly and quickly matters more than anything else right now."* |
| B (Days 8–30) | *"The home is often the last piece of a major life transition — once it's handled, everything else gets clearer."* |
| C (Days 31–90) | *"Every month this sits unresolved is another month you can't fully move forward. I want to help you close this chapter."* |
| D (Days 91–180) | *"I haven't forgotten about your situation. When you're ready to get this resolved — I'll make it as smooth as possible."* |

---

### FINANCIAL / EQUITY PULL
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"You've built real equity in that home — getting the full number out of it is what matters. That's exactly what I'm focused on."* |
| B (Days 8–30) | *"Equity doesn't earn anything sitting in the walls of a home. Getting it liquid and working for you is the move."* |
| C (Days 31–90) | *"The equity is still there. The window to pull it out at a strong number is what changes with the market."* |
| D (Days 91–180) | *"That equity isn't going anywhere — but market conditions do shift. Let's make sure you sell at the right time, not the convenient one."* |

---

### VACANT / ALREADY MOVED OUT
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"Every month that home sits empty is money out of your pocket — mortgage, taxes, insurance, utilities on a house nobody's living in."* |
| B (Days 8–30) | *"You've already made the move. The only thing left is making the old place stop costing you money."* |
| C (Days 31–90) | *"That vacant property hasn't stopped bleeding costs. The longer it sits, the more of your equity it eats."* |
| D (Days 91–180) | *"It's been months. That home is still costing you. When you're ready to make it stop — I know exactly how to move it fast."* |

---

### INVESTMENT
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"Getting the highest net number out of an investment property is a strategy question, not just a listing question. That's what I'm built for."* |
| B (Days 8–30) | *"Investors who time their exits well put that capital back to work faster. The sale is a financial decision — let's treat it like one."* |
| C (Days 31–90) | *"Capital sitting in a property that isn't appreciating is an opportunity cost. Is this still the right hold, or is now the time to move it?"* |
| D (Days 91–180) | *"Investment decisions deserve real data, not gut feelings. When you're ready to run the numbers on an exit — I can help."* |

---

### JUST CURIOUS / NO URGENCY
| Stage | Line |
|-------|------|
| A (Days 1–7) | *"Even without a hard deadline, knowing your home's real value in today's market gives you options. That's worth having."* |
| B (Days 8–30) | *"The best sellers aren't the ones with urgency — they're the ones who planned ahead. Knowing your number now puts you in that group."* |
| C (Days 31–90) | *"No rush on your end — but the market doesn't stay the same. Good to have a real number in your back pocket."* |
| D (Days 91–180) | *"Whether you sell this year or in two years — I'm still your first call when it matters. That's not changing."* |

---

## SEQUENCE SUMMARY — AT A GLANCE

| Day | Channel | Cancelled Appt | Post-Meeting No-List | Motivation Stage |
|-----|---------|---------------|---------------------|-----------------|
| 0 | Text | Missed you — reschedule? | Grateful — no pressure | A |
| 1 | Text / Email | Morning follow-up | Thank you + one specific insight | A |
| 3 | Text | Market note | Value update, no agenda | A |
| 5 | Text | Soft check — still interested? | — | — |
| 7 | Email | Market snapshot | Market update | A |
| 10 | Text | Value add | Resource offer | B |
| 14 | Email ⭐ | **TESTIMONIAL 1** | **TESTIMONIAL 1** | B |
| 21 | Text | Check-in | Casual check-in | B |
| 28 | Email | Monthly market | Monthly market | B |
| 45 | Text | Re-ask | **Best conversion window** | C |
| 60 | Email ⭐ | **TESTIMONIAL 2** | **TESTIMONIAL 2** | C |
| 75 | Text | Check-in | Thinking of you | C |
| 90 | Email / Text | Quarterly report | Direct check-in | C |
| 110 | Email | Market shift | Market shift | D |
| 130 | Text | Still here | Resource offer | D |
| 150 | Text / Email | Check-in | — | D |
| 165 | Email ⭐ | **TESTIMONIAL 3** | **TESTIMONIAL 3** | D |
| 180 | Text + Email | Close the loop | Close the loop | D |

⭐ = Insert testimonial from home evaluation survey sequence here
