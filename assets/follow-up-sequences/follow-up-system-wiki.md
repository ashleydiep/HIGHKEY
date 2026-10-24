# Follow-Up Sequence System — Agent Wiki
**High Key Solutions | Built by Ashley Diep**
_Last updated: August 2026_

> This system covers the two core follow-up campaigns used in the seller pipeline — the No-Show Appointment Sequence and the Follow-Up Campaign (Cancelled Appointment / Post-Meeting No-List). Both are built in GHL and run automatically with kill switches that stop the sequence the moment a lead re-engages.
>
> GHL snapshots are available for both campaigns. Import, customize your name and closing stories, then activate.

---

## Table of Contents

1. [Campaign 1 — No-Show Appointment Sequence](#campaign-1)
2. [Campaign 2 — Follow-Up Campaign (Cancelled / No-List)](#campaign-2)
3. [Kill Switch Setup (Both Campaigns)](#kill-switch)
4. [GHL Snapshot Import Instructions](#snapshot-import)
5. [Best Practices](#best-practices)

---

## Campaign 1 — No-Show Appointment Sequence {#campaign-1}

### Who This Is For
Sellers who had a **confirmed appointment** with you but did not show up.

### GHL Snapshot
> 📦 **Snapshot Link:** _[Add snapshot link here]_

### Sequence Structure (Days 1–21)

| Day | Send Time | Focus |
|-----|-----------|-------|
| Day 1 | Within 2 hours of no-show | Warm check-in — no judgment, offer to reschedule |
| Day 3 | 10:00 AM | Reschedule offer — two specific day options |
| Day 7 | 10:00 AM | Value drop — the 10-day listing window |
| Day 14 | 10:00 AM | Social proof — recent closing story |
| Day 21 | 10:00 AM | Final touch — soft close, no pressure |

---

## Campaign 2 — Follow-Up Campaign (Cancelled Appointment / Post-Meeting No-List) {#campaign-2}

### Who This Is For
- Sellers who **cancelled an appointment** before you could meet
- Sellers who **attended a listing presentation** but decided not to list with you

### GHL Snapshot
> 📦 **Snapshot Link:** _[Add snapshot link here]_

### Sequence Structure (Days 1–180)

**Phase 1 — Burst (Days 1–7)**

| Day | Type |
|-----|------|
| Day 1 | Text — send within 1 hour of trigger |
| Day 2 | Text |
| Day 4 | Text |
| Day 7 | Text + Email |

**Phase 2 — Weekly Nurture (Days 8–30)**

| Day | Focus |
|-----|-------|
| Day 8 | Education |
| Day 14 | Social proof |
| Day 21 | Soft check-in |
| Day 28–30 | Re-engagement ask |

**Phase 3 — Long-Burn Monthly (Days 31–180)**

| Day | Focus |
|-----|-------|
| Day 45 | Market update |
| Day 60 | Closing story |
| Day 90 | Check-in |
| Day 120 | Market update |
| Day 150 | Value drop |
| Day 180 | Final re-engagement |

---

## Kill Switch Setup (Both Campaigns) {#kill-switch}

Both campaigns use the same kill switch method. Set this up for each campaign after importing the snapshot.

**Create a Secondary Trigger Workflow:**

1. In GHL, create a **new workflow**
2. **Trigger:** Appointment Created
3. **Action:** Remove from Workflow → select the campaign by name
4. **Publish**

Repeat this for both campaigns — each needs its own secondary workflow pointing to it.

**This catches:**
- Appointments booked directly through your calendar link
- Appointments created manually by you in GHL
- Any new appointment created for that contact regardless of source

> ⚠️ Set up the kill switch **before** activating either campaign. A contact who rebooks should never continue receiving no-show or cancelled sequence messages.

---

## GHL Snapshot Import Instructions {#snapshot-import}

**How to Import:**
1. Go to **Settings → Snapshots** in GHL
2. Click **"Import Snapshot"**
3. Paste the snapshot share link from the campaign above
4. Select the sub-account to import into
5. Click **Import** — the workflow appears in your Workflows tab as inactive

**Before Activating — Customize:**
- [ ] Replace `[Agent Name]` with your name throughout all messages
- [ ] Replace `[Phone Number]` with your number
- [ ] Update closing story examples with your own recent deals
- [ ] Set send window to 9:00 AM – 6:00 PM in your timezone
- [ ] Set up kill switch workflow (see above) before going live
- [ ] Test with a dummy contact before activating

**Quiet Hours Setup:**
1. Go to **Settings → Business Info**
2. Scroll to **Quiet Hours**
3. Set active hours: 9:00 AM – 6:00 PM in your timezone
4. This prevents any sequence from sending outside business hours automatically

---

## Best Practices {#best-practices}

**Tone**
Every message is written to sound like it came from a real person. Do not make it more formal or add promotional language. The simplicity is intentional — trust it.

**One Sequence at a Time**
A contact should only ever be in one campaign. Before moving a contact from one sequence to another, use "Remove from all workflows" first.

**The Automation Opens the Door. You Close It.**
The moment a lead replies — move to manual immediately. The sequence surfaces interest. You close it.

**Update Your Closing Stories**
The social proof messages are only as strong as how recent and specific they are. Update your closing story examples every time you have a notable deal close.

**Response Rate Benchmark**
Healthy: 15–25% response rate.
Under 10%: check send times, tone, and whether leads are warm enough before entering the sequence.

---

_Wiki maintained by Ashley Diep / High Key Solutions. For GHL setup questions, contact the HKS team._
