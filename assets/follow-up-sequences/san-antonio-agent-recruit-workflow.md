# San Antonio Agent Recruit — Follow-Up Workflow
## Strata Group | GHL Sequence Spec

---

## Overview

**Who this is for:** Agents interviewed/discovered for the Strata Group opportunity in San Antonio
**Goal:** Keep them engaged after the first meeting → move to second meeting or decision
**Value proposition to reinforce:** Builder team producing 200 units/year — agents get built-in listings inventory + a warm investor pool of buyers already opting in to purchase units

---

## Trigger

**Start this workflow when:**
- Agent has completed a discovery/interview meeting
- Tag added: `SA-Recruit` in GHL
- Or pipeline stage moved to: "Discovery Met" in the San Antonio recruiting pipeline

---

## Kill Switch

**Remove from workflow when:**
- Agent books a second meeting → tag `SA-Second-Meeting`
- Agent says yes / accepts offer → tag `SA-Joined`
- Agent says no / not interested → tag `SA-Dead`

> Use Method 2: Create a secondary trigger workflow — Trigger = Tag Added (`SA-Second-Meeting` OR `SA-Joined` OR `SA-Dead`) → Remove from SA Recruit Workflow

---

## Sequence

### Day 1 — Same Day or Next Morning
**Channel:** SMS

> "Hey [first name]! It was great connecting with you today. Just wanted to follow up and make sure you have everything you need. The Strata Group opportunity is one of the most unique setups I have seen — 200 units a year means your pipeline is essentially built for you. Let me know when you are ready to take the next step. — Ashley"

---

### Day 2 — Email
**Channel:** Email
**Subject:** What most agents never get access to

> "Hi [first name],
>
> I wanted to put into words what we talked about yesterday.
>
> Most agents spend 80% of their time chasing listings. With the Strata Group, that problem is solved. The builders are producing 200 units a year — that is consistent, recurring inventory that needs to be sold. You step in as the agent of record.
>
> On top of that, there is an active investor pool of buyers already opting in to purchase these units. You are not prospecting buyers from scratch — they are raising their hand.
>
> This is not a traditional team model. It is a production machine that needs the right agent.
>
> When are you free to talk this week?
>
> — Ashley"

---

### Day 5 — SMS Check-In
**Channel:** SMS

> "Hey [first name], just checking in! Have you had a chance to think more about the Strata opportunity? Happy to jump on a quick call to answer any questions."

---

### Day 10 — Email: The Investor Angle
**Channel:** Email
**Subject:** The other side of this opportunity

> "Hi [first name],
>
> One thing I want to make sure you understand about the Strata Group — it is not just about selling new construction.
>
> There is an investor side to this. Buyers are already opting in specifically to purchase units from this builder. As the agent, you are the connection point between the builder and those investors. That is a repeat buyer pipeline that most agents spend years trying to build.
>
> I would love to walk you through exactly how this works. Are you available for a 20-minute call this week?
>
> — Ashley"

---

### Day 14 — SMS
**Channel:** SMS

> "Hey [first name]! Wanted to reach out again — we are actively looking for the right agent to fill this role in San Antonio. The opportunity does not stay open forever. Would love to reconnect soon."

---

### Day 21 — Email: Urgency
**Channel:** Email
**Subject:** Still thinking it over?

> "Hi [first name],
>
> I know decisions like this take time — I respect that.
>
> I want to be transparent with you: we are in the process of interviewing agents right now and this position will be filled. I would hate for you to miss out on something that could change the trajectory of your business.
>
> The builder is producing. The investors are in place. We just need the right agent.
>
> Can we get 20 minutes on the calendar this week?
>
> — Ashley"

---

### Day 30 — SMS Final Check-In
**Channel:** SMS

> "Hey [first name], last check-in from me! The Strata Group opportunity is still open. If timing is not right now, no worries at all — but I did not want to close the door without giving you one more chance to connect. Let me know either way!"

---

### Day 45 — Email: Long Burn
**Channel:** Email
**Subject:** Quick update on the Strata Group

> "Hi [first name],
>
> Just a quick note — wanted to keep you in the loop. The builder team is ramping up for the next phase of builds and we are getting serious about locking in our agent team.
>
> If the timing feels better now than it did a few weeks ago, I would love to reconnect.
>
> — Ashley"

---

### Day 60 — SMS
**Channel:** SMS

> "Hey [first name]! Hope things are going well. We still have an opening for the right agent in San Antonio. Reach out anytime — the door is open."

---

### Day 90 — Final Email
**Channel:** Email
**Subject:** Keeping the door open

> "Hi [first name],
>
> I have enjoyed getting to know you and I still think you would be a great fit for what we are building with the Strata Group.
>
> If now is not the right time, I completely understand. I will keep you on my radar — and when you are ready to revisit, just reach out.
>
> Wishing you the best in your business.
>
> — Ashley"

> After Day 90: Move contact to `SA-Long-Term-Nurture` tag. Remove from active sequence.

---

## GHL Build Instructions

### Step 1: Create the Workflow
- Name: `SA Agent Recruit — Post Discovery Follow-Up`
- Trigger: Tag Added → `SA-Recruit`

### Step 2: Add Steps in Order
1. Wait 0 days → Send SMS (Day 1)
2. Wait 1 day → Send Email (Day 2)
3. Wait 3 days → Send SMS (Day 5)
4. Wait 5 days → Send Email (Day 10)
5. Wait 4 days → Send SMS (Day 14)
6. Wait 7 days → Send Email (Day 21)
7. Wait 9 days → Send SMS (Day 30)
8. Wait 15 days → Send Email (Day 45)
9. Wait 15 days → Send SMS (Day 60)
10. Wait 30 days → Send Email (Day 90)
11. Final step: Add Tag → `SA-Long-Term-Nurture` → Remove from Workflow

### Step 3: Set Up Kill Switch (Method 2)
Create a separate workflow:
- Name: `SA Recruit — Kill Switch`
- Trigger: Tag Added → `SA-Second-Meeting` OR `SA-Joined` OR `SA-Dead`
- Action: Remove from Workflow → `SA Agent Recruit — Post Discovery Follow-Up`

### Step 4: Pipeline Setup (Recommended)
Create a San Antonio Recruiting pipeline in GHL with stages:
- New Lead
- Discovery Set
- Discovery Met → (triggers this workflow)
- Second Meeting Set
- Offer Extended
- Joined
- Not a Fit

---

## Pre-Launch Checklist
- [ ] Workflow built in GHL
- [ ] All messages loaded and reviewed
- [ ] Kill switch workflow active
- [ ] San Antonio pipeline created
- [ ] Test contact run through full sequence before going live

---

*Last updated: October 2026*
