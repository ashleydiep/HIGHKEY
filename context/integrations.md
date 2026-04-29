# Integrations

> This file maps every external service, tool, and data source your business uses. The AI OS uses this to understand what data is available, what can be connected, and what to build sync scripts for.

---

## How This Connects

- **companies.md** describes the businesses these tools serve
- **current-data.md** tracks metrics that come from these integrations
- **This file** maps the data landscape and connection status. It's the input to `/connect-data`.
- **`/connect-data`** reads this file, classifies each service by data pattern, checks the MCP Registry, and handles the connections automatically
- **scripts/README.md** explains what the generated sync scripts look like under the hood
- **reference/mcp-guide.md** explains what MCP is and when it's the right method

---

## Why This Matters

Your AI OS is only as powerful as the data flowing into it. This file serves two purposes:

1. **Today:** Helps Claude understand what tools you use and what data exists
2. **When building the Data layer:** Serves as the roadmap for which services to connect and in what order

---

## Integration Status

[List every tool and service your business uses. Mark the status of each. You don't need to understand the `Data Pattern` values — `/build-context` classifies each service for you automatically (or asks you one plain-English question for unfamiliar ones), and `/connect-data` reads the result. If you're filling this file manually, just name the service and leave Data Pattern blank; the commands handle the rest.]

| Service | Category | Purpose | Data Pattern | Connection | Status | Priority | Notes |
|---------|----------|---------|--------------|------------|--------|----------|-------|
| Go High-Level (GHL) | CRM | Client tracking, transactions, lead management | Both | API + Live wrapper | Connected (Sync — scripts/sync/ghl.py \| Live — scripts/live/ghl.ts) | High | Main CRM for all business operations |
| Skyslope | Forms/Signatures | Documents and e-signatures for transactions | Append-only | API | Not connected | High | For forms and signatures |
| MLS | Real Estate | Market reports, property data | Append-only | API | Not connected | High | Houston MLS system |
| HAR (Houston) | Real Estate | Market reports, property data | Append-only | API | Not connected | High | Houston Area Realtor data |
| EXP Dashboard | Analytics | Deal tracking, production metrics | Append-only | API | Not connected | High | EXP Realty dashboard for analytics |
| Google Calendar | Productivity | Meeting scheduling, appointments | Ever-changing | MCP | Live (MCP — google-calendar) | Medium | Track all appointments |
| Gmail | Communication | Email management | Both | API + MCP | Connected (Sync — scripts/sync/gmail.py \| Live — MCP gmail-mcp-server) | Medium | Sync last 12mo non-promotional emails to Supabase; MCP for live queries |
| Notion | Knowledge | Notes, SOPs, documentation | Ever-changing | MCP | Live (MCP — notion) | Medium | Business notes and documentation |
| Facebook | Social Media | Facebook Page posts + analytics + Ads | Append-only | API | Connected (Sync — scripts/sync/meta.py + scripts/sync/facebook_ads.py) | Medium | Page posts, ad campaign performance synced to Supabase |
| Instagram | Social Media | Instagram posts + analytics | Append-only | API | Connected (Sync — scripts/sync/meta.py) | Medium | Posts, likes, comments, saves, reach synced to Supabase |
| Google Ads | Marketing | Ad campaign performance, spend, conversions | Append-only | API | Connected (Sync — scripts/sync/google_ads.py) | High | 90-day rolling daily campaign data in Supabase |
| YouTube | Social Media | Video marketing, brand building | Append-only | API | Connected (Sync — scripts/sync/youtube.py) | Medium | Two channels: ProAgent Real Estate + Ashley Diep personal. Separate OAuth tokens per channel. |

> **Data Pattern values:**
> - **Append-only** — data written once, never modified (transcripts, messages, transactions, CRM activity logs). Needs API sync into Supabase so it accumulates and can be searched across time.
> - **Ever-changing** — data revised in place (SOPs, knowledge bases, today's calendar, current pipeline state). Needs MCP for live queries. Never sync a stale copy.
> - **Both** — services that hold both patterns. Slack messages are append-only; channel status is ever-changing. These services get dual-method connection (API sync for history + MCP for live).
>
> **Connection values:**
> - `MCP` — zero-code live connection via `.mcp.json` (see `reference/mcp-guide.md`)
> - `API` — sync script writes into Supabase on a schedule (Routine)
> - `API + MCP` — dual-method for services with both data patterns
> - `Manual` — no API, no MCP; drop files into `data/imports/<service>/` to ingest
>
> See Module 3 or run `/connect-data` to have the system classify automatically.

---

## Common Categories for Agencies

Use this as a checklist to make sure you've covered your bases:

### AI & Automation

| Service | What It Does | Priority | Connection Type | Status |
|---------|-------------|----------|-----------------|--------|
| AgencyOSX | 15 AI employees for agency operations. Connects via MCP (see `reference/architecture.md`) | Medium | MCP server | [ ] Not connected |
| Claude Code | AI development and operations partner (this project) | High | Native | [x] Active |
| [Other AI tools] | [Description] | [Priority] | [Type] | [ ] |

### High Priority (connect first)
- **CRM / Sales** — Where your pipeline and client data lives (HubSpot, Pipedrive, Close, GoHighLevel, Airtable)
- **Payments / Billing** — Revenue data (Stripe, PayPal, Xero, QuickBooks)
- **Communication** — Team and client messages (Slack, email, WhatsApp)

### Medium Priority (connect second)
- **Calendar** — Meeting data (Google Calendar, Calendly)
- **Documents** — Meeting transcripts, SOPs, client files (Google Drive, Notion)
- **Project Management** — Task and workload data (ClickUp, Asana, Monday.com)
 
### Lower Priority (connect when ready)
- **Marketing** — Ad performance, analytics (Meta Ads, Google Ads, GA4)
- **Social Media** — Content performance (YouTube Analytics, LinkedIn, Instagram)
- **Support** — Client support data (Intercom, Zendesk, Crisp)
- **Hiring** — Recruitment data (job boards, applicant tracking)

---

## Connection Priority Order

[Based on your business, which integrations should be connected first? Consider: what data would be most valuable in your Daily Brief?]

1. **[Service]** — [Why it's highest priority]
2. **[Service]** — [Why it's second]
3. **[Service]** — [Why it's third]
4. **[Service]** — [Why it matters]
5. **[Service]** — [Why it matters]

---

## Environment Variables

When you start connecting services, you'll need API keys and credentials. Store them in a `.env.local` file in the project root (this file is gitignored and never committed).

```bash
# Example .env.local structure
# CRM
CRM_API_KEY=

# Payments
STRIPE_SECRET_KEY=

# Communication
SLACK_BOT_TOKEN=
GMAIL_USER=

# AI
ANTHROPIC_API_KEY=

# Database (when you need one)
# SUPABASE_URL=
# SUPABASE_SERVICE_ROLE_KEY=
```

---

## MCP Connections

Many services support MCP — a zero-code way to connect directly to Claude Code. Instead of writing sync scripts, you add a JSON config and Claude can query the service live. See `reference/mcp-guide.md` for the complete setup guide and a list of supported services.

---

_Update this as you add or change tools. This is the roadmap for your Data layer._
