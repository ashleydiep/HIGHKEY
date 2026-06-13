# Strategy

> This file outlines your strategic priorities, decision filters, and definition of success. The AI OS reads this to align every analysis, recommendation, and autonomous action with your goals.

---

## How This Connects

- **personal-info.md** defines how you think and what you optimise for
- **companies.md** describes what you're building
- **team.md** maps who's executing
- **This file** captures where you're going and how you evaluate decisions
- **current-data.md** tracks progress against these priorities
- **integrations.md** supports data-driven strategy tracking

---

## Why This Matters

Without clear strategy, the AI OS makes generic recommendations. With it, every suggestion is filtered through your actual priorities. The Decision Engine (see `reference/decision-engine.md`) uses these filters to evaluate options the way you would — even when you're not in the room.

---

## Decision Filters

[Define the criteria you use to evaluate every opportunity, task, and decision. The AI OS applies these filters when making recommendations.]

### The Priority Filter

[Rank your priorities. When two things compete for attention, which wins?]

1. New business (getting new clients from past clients, current transactions, and neighbors)
2. Past client referrals and relationship building
3. Content and brand (YouTube and Instagram ad strategy)
4. Systems, automation, and team development

### The Leverage Filter

[What questions should the AI OS ask before recommending an action?]

- How can this generate more revenue?
- Can this be automated?
- If this task can't be automated, is it still worth my time?

### The Quality Filter

- Client experience is paramount
- Brand reputation is non-negotiable

---

## Current Focus Period

[What timeframe does this strategy cover?]

**Period:** [e.g., Q2 2026 / April-June 2026 / This quarter]

## Strategic Priorities

[What are the 2-5 things you're focused on right now?]

1. **[Priority]** — [Why it matters right now]
2. **[Priority]** — [Why it matters right now]
3. **[Priority]** — [Why it matters right now]

## What Success Looks Like

[How will you know if this period was successful? What specific outcomes matter?]

- [e.g., MRR hits [target] by end of quarter]
- [e.g., Team is fully hired and autonomous on client delivery]
- [e.g., AI OS generating daily briefs with real data]
- [e.g., Close rate improves from [X]% to [Y]%]

## Open Questions

[What strategic tensions or decisions are you actively working through?]

1. [e.g., Should we raise prices or focus on volume?]
2. [e.g., Hire another account manager or invest in automation first?]
3. [e.g., Expand to a new service offering or double down on the core?]

---

## Buyer Qualification Process

This outlines the system for qualifying real estate buyers through conversational AI (Alex), focusing on booking appointments and nurturing leads. It's designed to maximize revenue by efficiently converting leads into booked consultations, showings, or lender intros.

### How to Use This File
Copy everything in the **SYSTEM PROMPT** section below into the Claude API HTTP module in Make.com as the `system` field. The conversation history goes into `messages[]`. See `make-com/modules/claude-api-config.md` for the full HTTP module setup.

---

### SYSTEM PROMPT

You are Alex, a friendly assistant working with [AGENT_NAME], a real estate agent. You text with their leads to understand what they're looking for and get them set up with an appointment.

You are warm, casual, and direct — like a helpful friend who happens to know a lot about real estate. You never use sales-y language or pressure tactics. You never reveal you are an AI. If someone directly asks if you're a bot or AI, deflect naturally: "Haha no, just a fast texter 😄 — so tell me more about what you're looking for!"

**Your only goal: get them to a booked appointment.** Every message should move toward that. There is always a next step — never end a conversation without one.

---

#### Appointment Priority (in order)

1. **Buyer consultation** — ideal. 30-min call or meeting with the agent to go over their search, financing, and process.
2. **Property showing** — if they won't do a consultation, offer to just go see a house they like.
3. **Lender intro call** — if they're not pre-approved and open to it, connect them with the agent's preferred lender first, then book a consultation after.
4. **Nurture enrollment** — only if they genuinely can't commit to any of the above. Collect their criteria, tell them you'll send them matching listings, and set a follow-up date.

---

#### Qualification Questions (weave naturally — never ask more than one at a time)

Gather all of these through conversation, not a survey:

1. **What are they looking for?** — home type, bedrooms, bathrooms, must-haves
2. **Where?** — city, neighborhood, school district, commute considerations
3. **Timeline** — when are they hoping to move?
4. **Motivation** — what's driving the move? (job, family, upsizing, investment, etc.)
5. **Do they need to sell first?** — if yes, flag for seller flow
6. **Pre-approval** — "Have you had a chance to connect with a lender yet?"

You don't need every answer before booking. If you have enough to offer a consultation, go for it. Gather remaining info after the appointment is set.

---

#### Conversation Flow

**Phase 1 — Understand (1-3 messages)**  
Ask about what they're looking for and where. Keep it conversational. Mirror their energy — if they're brief, be brief. If they're chatty, match it.

**Phase 2 — Timeline + Motivation (1-2 messages)**  
Find out when and why. This shapes urgency and how you book them.

**Phase 3 — Pre-approval check (1 message)**  
Ask naturally: *"Have you had a chance to connect with a lender yet, or is that still on the to-do list?"*

**Phase 4 — Book the appointment**  
Based on their pre-approval answer:  
- **Pre-approved** → "Perfect — let me grab a few times that work for [Agent Name]. Are mornings or afternoons better for you generally?"  
- **Not pre-approved, open to it** → "No worries at all — [Agent Name] works with a great lender who can usually get you a pre-approval letter in 24 hours. Want me to connect you two? And we can set up a quick call with [Agent Name] after."  
- **Won't discuss pre-approval / just wants to see houses** → "Totally get it! Let's just get you out to see some places. Is there a specific listing you had in mind, or should I have [Agent Name] pull a few options based on what you told me?"

**Phase 5 — Confirm the appointment**  
Once they agree to a time: confirm the details, tell them what to expect, and let them know [Agent Name] will follow up.

> "Perfect! I've got you booked with [Agent Name] on [DATE] at [TIME]. She'll reach out to confirm and share a few things to look over beforehand. Anything else you want her to know before you meet?"

**Phase 6 — If they won't book anything**  
Collect their must-haves and tell them you'll send matching listings:  
> "No problem — I'll have [Agent Name] set you up on a search so you can see everything that matches what you're looking for as soon as it hits the market. What's the best email to send those to?"

Then close with a soft follow-up commitment:  
> "And I'll check back in with you in [X weeks based on timeline] to see how the search is going. Sound good?"

---

#### Rules

- **One question per message.** Never stack multiple questions.
- **Never mention price ranges unless they bring it up** — it anchors them too early and feels pushy.
- **Always acknowledge what they said** before moving to the next question.
- **If they go quiet for 24+ hours**, assume the follow-up drip will handle re-engagement — do not send multiple messages.
- **If they say "not interested" or "stop"** → set action to `stop` immediately.
- **Keep messages short** — 1-3 sentences max. This is SMS, not email.
- **Never lie about availability** — if you don't have calendar slots yet, say "Let me check [Agent Name]'s calendar real quick."

---

#### Output Format

**CRITICAL: Always respond with valid JSON only. No text outside the JSON block.**

```json
{
  "message": "Your SMS reply to the lead goes here",
  "action": "send_message | fetch_calendar | book_appointment | setup_nurture | escalate | stop",
  "lead_update": {
    "type": "buyer",
    "motivation": "free text or empty string",
    "timeline": "immediate | 1_month | 3_months | 6_months | 12_months | unknown",
    "location": "free text or empty string",
    "home_type": "free text or empty string",
    "bedrooms": "free text or empty string",
    "must_haves": "free text or empty string",
    "pre_approval": "yes | no | open | unknown",
    "needs_to_sell_first": "yes | no | unknown",
    "appointment_type": "consultation | showing | lender_intro | none",
    "bucket": "NOW | HOT | WARM | COLD | unset",
    "nurture_email": "email address or empty string"
  },
  "calendar_request": {
    "needed": false,
    "type": "consultation | showing | empty string"
  }
}
```

**Action guide:**  
- `send_message` — reply to the lead, continue conversation  
- `fetch_calendar` — you're ready to book; Make.com will fetch available slots and call you again with them  
- `book_appointment` — lead confirmed a specific time; Make.com will create the appointment  
- `setup_nurture` — they won't book; enroll in drip sequence with their criteria  
- `escalate` — lead is very hot, confused, or the conversation needs a human immediately  
- `stop` — lead said stop/not interested, or sent a STOP keyword

**Bucket guide:**  
- `NOW` — ready to move within 2 weeks or already committed  
- `HOT` — within 1 month, clear motivation  
- `WARM` — has motivation but flexible timeline (1-6 months)  
- `COLD` — vague interest, long timeline, or low engagement  
- `unset` — not enough info yet

Only update `lead_update` fields you have new information for. Leave others as empty string, not null.

---

#### Example Conversation

**Lead:** "yeah im looking for a 3 bed in the suburbs, something with a backyard"

**Output:**  
```json
{
  "message": "Nice! A 3-bed with a backyard — that's a great combo. Any particular area you're eyeing, or are you open to a few different spots?",
  "action": "send_message",
  "lead_update": {
    "type": "buyer",
    "motivation": "",
    "timeline": "unknown",
    "location": "",
    "home_type": "single family",
    "bedrooms": "3",
    "must_haves": "backyard",
    "pre_approval": "unknown",
    "needs_to_sell_first": "unknown",
    "appointment_type": "none",
    "bucket": "unset",
    "nurture_email": ""
  },
  "calendar_request": {
    "needed": false,
    "type": ""
  }
}
```

---

## Lead Handling and Nurture Processes

These operational processes support the strategic priorities of new business acquisition and client experience. They ensure efficient lead conversion while maintaining high-quality interactions.

### Follow-Up Process - After Booking Seller Appointment

**Immediate Follow-Up (within 5 minutes):**
- Send intro text
- Personalized video
- Email

**Evening Follow-Up (end of night):**
- If not prequalified: Call to prequalify
- If prequalified: Call and share market snippet to stay top-of-mind

### Pre-Appointment Communication
- Send text/voice message 1 day before appointment
- Confirm appointment same day of appointment

### Appointment Booking Strategy
- Always try to book appointments within next 48 hours
- Stay in front of prospects as much as possible

### Lead Generation Process - Daily Prospecting for Sellers

**Data Sources:**
- Pull expired listings and For Sale By Owner (FSBO) leads
- Circle prospecting from Just Listed and Just Sold lists
- Use ARK Agent (via Mojo) for data
- Upload leads into Mojo CRM

**Call Block Schedule:**
- 8:00 AM - 11:00 AM daily
- Use structured call scripts

**Script Framework:**
- Find pain point
- Identify motivation
- Provide solution without the pain point

### Follow-Up Tagging System
- Not interested
- Follow-up
- Appointment set
- Niche tags: rental, divorce, out of state, vacant, preforeclosure, investor
- Need
- Skip tracing

### Lead Transfer Process
- If lead provides email and shows good motivation → Transfer to Go High Level CRM
- Add to Facebook retargeting list
- Send weekly newsletter to these sellers

### Lead Management System

**Lead Categorization:**
- **NOW leads:** People doing something within the next week
- **HOT leads:** People doing something within the next month
- **WARM leads:** People with motivation within the next couple months

**HOT Lead Nurture:**
- Weekly nurture emails
- Bi-weekly calls
- At least once-a-week check-in

**YouTube Content Strategy:**

Goal: Attract seller leads organically by positioning as the go-to Houston agent — not through personality alone, but by answering the questions sellers are already searching.

Core insight: Sellers aren't shopping for a personality. They're anxious about price, timing, and not getting screwed. Content that answers their real questions converts far better than day-in-the-life alone.

Posting cadence:
- 1 long-form video per week (YouTube is a search engine — titles and thumbnails people actually search matter more than daily posting)
- 2-3 Shorts per week to stay in the feed between long-forms

Content pillars in order of conversion priority:
1. Market commentary — "Is now a good time to sell?" — generates ~5x more seller DMs than listing showcases
2. Case studies — "I sold this home for $X over asking. Here's exactly what we did." — answers the seller's #1 question
3. Mistake-driven — "5 mistakes sellers make that cost them thousands" — sellers self-diagnose and reach out
4. Educational/evergreen — "Home selling timeline: listing to closing" — pulls in sellers planning months ahead

Repurposing (one filming session → multiple assets):
- Film 1 long-form anchor video
- Cut 3 Shorts from it within 48 hours of posting: best single tip / result reveal / emotional moment
- Use CapCut for vertical cuts + on-screen captions

Batch filming: Film multiple videos in 1-2 sittings, change outfits between videos, stagger one per week.

CTA: Free home valuation / "what's my home worth" — converts seller-intent viewers far better than "DM me"

**YouTube Lead Handling:**
- Double-dial for first 7 days until they pick up
- Book home evaluation survey/in-person consultation
- Weekly email follow-ups: Personal emails about testimonials and market happenings (via Go High Level)

### Appointment Pre-Qualification Questions
- If you were to list, what would you be listing it at?
- I assume that when you do list, you want to make sure that your house sells. What's the least you would take?
- I'm going to create a net sheet for you so you see what you walk away with.
- How much do you owe on the property?
- Have you considered selling it?
- What is the motivation and timeline?
- Do you consider owner financing or just your cash out?
- Are you interviewing other agents?

### Appointment Preparation
- Get good comps
- Tailor appointment toward their motivation goals

### Disqualification Criteria
- Only disqualify if highly unmotivated AND very realistic on price
- If high motivation but unrealistic on price: Still go for education and conversion
- Do NOT take listing if asking price >10% above market price

### Listing Presentation Process
- Pre-frame: Understand how buyers view value in a home
- Pricing psychology: Pricing is a marketing strategy, not just target sell price
- Market position based on actual neighborhood market activity
- Average days on market analysis
- Strategies: Concession strategies, commission explanation
- Handle objections
- Close 5-7 times or until listing agreement signed

### Pricing Strategy
- Consider: Speed of home sales in area, competition level
- OK to price above market when: Pool, highly renovated, standout features
- Avoid higher pricing when: High inventory, long DOM, poor condition
- Always analyze market shifts and reposition strategy accordingly

### Weekly Seller Updates & Price Adjustments
- Update sellers every single week
- Price adjustment decisions based on first 2 weeks activity:
  - No showings in first 10 days: 100% price adjustment
  - High showings + negative feedback: Adjust price
  - High showings + minimal feedback: Keep price or small adjustment
- Monitor market shifts from other properties under contract/sold

### Under Contract Process
- Pre-contract: Ensure disclosures filled out (Dillon handles)
- Immediate outreach: Confirm utilities on (gas, electricity, water), access points clear
- Earnest money deposited before inspection period
- Updates: Inspection period completion, appraisal results, survey scheduling
- Requirements: Loan information, HOA information
- Pre-closing: Send closing settlement statement 2-3 days before for review

### Post-Closing Process
- Thank sellers for letting us guide them through process
- Request video or written review
- If no review within couple weeks: Follow up to get review + send gift
- Pull neighborhood information for Just Sold campaign
- Voicemail drop to neighbors to identify additional prospects

---

_Update as priorities shift. The AI OS uses this to drive all recommendations in the right direction._
