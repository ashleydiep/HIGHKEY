/**
 * ProAgent AI OS — Cloudflare Worker
 *
 * Routes:
 *   POST /           → Telegram bot (KPI logging, decisions, Claude Q&A)
 *   POST /fireflies  → Fireflies.ai webhook (transcription done → update GHL + notify Ashley)
 */

const SYSTEM_PROMPT = `You are the AI OS for Ashley Diep, a real estate agent and entrepreneur in Houston.

Ashley runs three businesses:
- PROAGENT (real estate sales — sellers and buyers, 3% commission, target 2-3 closings/month)
- COLLAB (agent recruitment, target 50 agents by end of 2026, currently at 16)
- High Key Solutions (AI systems for real estate agents — pre-revenue)

Her daily schedule:
- 8:00–11:00am: Seller cold calling (target: 2 appts set/day, ~25 contacts per appt)
- 9:30–10:00am: Breakfast Club (daily sales training)
- 11:30am–12:00pm: Agent recruiting calls

Her seller funnel: contacts → leads → appts set → appts met → listings → closings
Her agent funnel: contacts → discoveries set/met → 3-ways set/met → verbals → onboarded

YOU HAVE A DATABASE TOOL. When Ashley gives you her daily numbers — in any format, however casual — extract every number she mentions and call save_daily_kpis immediately. Don't ask her to repeat or reformat. Parse intelligently.

Examples of what to detect and save:
- "I made 45 contacts, set 2 appts" → save contacts=45, appts_set=2
- "log my numbers: 50 dials, 3 leads, 2 appts set, 1 met" → parse and save all
- "today I called 30 agents and set 2 discoveries" → save agent_contacts=30, agent_discoveries_set=2
- "/numbers 40 contacts 2 appts set 1 met" → save those fields

After saving, confirm exactly what was saved in a short message. If the save fails, tell her clearly.

Be direct and concise. Ashley is usually between calls.`;

const TOOLS = [
  {
    name: 'save_daily_kpis',
    description: "Save Ashley's daily activity numbers to the database. Call this whenever she provides any of her daily KPI numbers, in any format.",
    input_schema: {
      type: 'object',
      properties: {
        date: { type: 'string', description: 'Date in YYYY-MM-DD format. Use today if not specified.' },
        contacts: { type: 'integer', description: 'Seller dials/contacts made' },
        leads: { type: 'integer', description: 'Leads (people who engaged)' },
        emails: { type: 'integer', description: 'Emails sent' },
        appts_set: { type: 'integer', description: 'Seller appointments set' },
        appts_met: { type: 'integer', description: 'Seller appointments attended/met' },
        fsbo_preview_set: { type: 'integer', description: 'FSBO preview appointments set' },
        fsbo_met: { type: 'integer', description: 'FSBO appointments met' },
        fsbo_listing: { type: 'integer', description: 'FSBO listings taken' },
        listings_other: { type: 'integer', description: 'Listings from other sources' },
        listings: { type: 'integer', description: 'Total listings taken' },
        buyer_appts_set: { type: 'integer', description: 'Buyer appointments set' },
        buyer_appts_met: { type: 'integer', description: 'Buyer appointments met' },
        buyer_contracts_signed: { type: 'integer', description: 'Buyer contracts signed' },
        agent_contacts: { type: 'integer', description: 'Agent recruiting calls/contacts made' },
        agent_discoveries_set: { type: 'integer', description: 'Agent discovery calls set' },
        agent_discoveries_met: { type: 'integer', description: 'Agent discovery calls met/attended' },
        agent_3ways_set: { type: 'integer', description: '3-way calls with broker set' },
        agent_3ways_met: { type: 'integer', description: '3-way calls met/attended' },
        agent_verbals: { type: 'integer', description: 'Agent verbal commitments to join' },
        agent_onboarded: { type: 'integer', description: 'Agents actually onboarded' },
        closings: { type: 'integer', description: 'Transactions closed today' },
        notes: { type: 'string', description: 'Any notes about the day' },
      },
      required: ['date'],
    },
  },
];

const ALLOWED_CHAT_IDS = new Set([5304294443]);

// Regex for decision commands
const ACCEPT_RE = /^accept\s+(rec_[a-zA-Z0-9]+(?:\s+rec_[a-zA-Z0-9]+)*)\s*$/i;
const REJECT_RE = /^reject\s+(rec_[a-zA-Z0-9]+)\s+(disagree|no-time|redundant|wrong-context|later)(?:\s+(\d+))?(?:\s+(.+))?$/i;
const PENDING_RE = /^(pending|\/pending)\s*$/i;

const conversations = new Map();
const MAX_HISTORY = 10;

// ── Decision Engine (Supabase direct) ────────────────────────────────────────
async function sbGet(supabaseUrl, supabaseKey, path) {
  const resp = await fetch(`${supabaseUrl}/rest/v1/${path}`, {
    headers: { apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}` },
  });
  return resp.ok ? resp.json() : [];
}

async function sbPatch(supabaseUrl, supabaseKey, path, body) {
  await fetch(`${supabaseUrl}/rest/v1/${path}`, {
    method: 'PATCH',
    headers: {
      apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}`,
      'Content-Type': 'application/json', Prefer: 'return=minimal',
    },
    body: JSON.stringify(body),
  });
}

function addDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

async function handleDecisionCommands(supabaseUrl, supabaseKey, text) {
  // PENDING
  if (PENDING_RE.test(text.trim())) {
    const rows = await sbGet(supabaseUrl, supabaseKey,
      'decisions?source=eq.ai-recommendation&status=eq.pending&select=short_id,question&order=created_at.asc');
    if (!rows.length) return 'No pending recommendations. Clean slate ✓';
    const list = rows.map(r => `[${r.short_id}] ${r.question}`).join('\n');
    return `*Pending Recommendations (${rows.length}):*\n\n${list}\n\n_Reply: \`accept rec_xxx\` or \`reject rec_xxx disagree\`_`;
  }

  // ACCEPT
  const acceptMatch = text.trim().match(ACCEPT_RE);
  if (acceptMatch) {
    const ids = acceptMatch[1].trim().split(/\s+/);
    const results = [];
    for (const shortId of ids) {
      const rows = await sbGet(supabaseUrl, supabaseKey,
        `decisions?short_id=eq.${shortId}&source=eq.ai-recommendation&status=eq.pending&select=id,short_id`);
      if (!rows.length) { results.push(`${shortId}: not found`); continue; }
      await sbPatch(supabaseUrl, supabaseKey, `decisions?id=eq.${rows[0].id}`,
        { status: 'accepted', outcome_assessed_at: addDays(30) });
      results.push(`${shortId}: ✓ accepted`);
    }
    return results.join('\n');
  }

  // REJECT
  const rejectMatch = text.trim().match(REJECT_RE);
  if (rejectMatch) {
    const [, shortId, category, daysStr, note] = rejectMatch;
    const rows = await sbGet(supabaseUrl, supabaseKey,
      `decisions?short_id=eq.${shortId}&source=eq.ai-recommendation&status=eq.pending&select=id,short_id`);
    if (!rows.length) return `${shortId}: not found or already actioned`;
    const patch = { status: 'rejected', reason_category: category };
    if (note) patch.rejection_note = note;
    if (category === 'later') {
      const days = daysStr ? parseInt(daysStr) : 7;
      patch.re_surface_at = addDays(days);
    }
    await sbPatch(supabaseUrl, supabaseKey, `decisions?id=eq.${rows[0].id}`, patch);
    return `${shortId}: rejected (${category})${category === 'later' ? ` — resurfaces in ${daysStr || 7} days` : ''}`;
  }

  return null; // not a decision command
}

// ── Supabase ──────────────────────────────────────────────────────────────────
async function saveDailyKpis(supabaseUrl, supabaseKey, data) {
  const resp = await fetch(`${supabaseUrl}/rest/v1/daily_kpis`, {
    method: 'POST',
    headers: {
      apikey: supabaseKey,
      Authorization: `Bearer ${supabaseKey}`,
      'Content-Type': 'application/json',
      Prefer: 'resolution=merge-duplicates,return=representation',
    },
    body: JSON.stringify(data),
  });
  const result = await resp.json();
  if (!resp.ok) throw new Error(result.message || JSON.stringify(result));
  return result;
}

// ── Telegram ──────────────────────────────────────────────────────────────────
async function sendMessage(botToken, chatId, text) {
  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }),
  });
}

// ── Claude with tool use ──────────────────────────────────────────────────────
async function callClaude(anthropicKey, supabaseUrl, supabaseKey, chatId, userMessage) {
  if (!conversations.has(chatId)) conversations.set(chatId, []);
  const history = conversations.get(chatId);

  history.push({ role: 'user', content: userMessage });

  // Keep looping while Claude wants to use tools
  let finalReply = '';
  let messages = [...history];

  while (true) {
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': anthropicKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 1024,
        system: SYSTEM_PROMPT,
        tools: TOOLS,
        messages,
      }),
    });

    const data = await resp.json();
    const stopReason = data.stop_reason;
    const content = data.content || [];

    // Add assistant response to messages
    messages.push({ role: 'assistant', content });

    if (stopReason === 'tool_use') {
      // Process each tool call
      const toolResults = [];
      for (const block of content) {
        if (block.type !== 'tool_use') continue;

        let toolResult;
        if (block.name === 'save_daily_kpis') {
          try {
            await saveDailyKpis(supabaseUrl, supabaseKey, block.input);
            toolResult = { success: true, saved: block.input };
          } catch (err) {
            toolResult = { success: false, error: err.message };
          }
        }

        toolResults.push({
          type: 'tool_result',
          tool_use_id: block.id,
          content: JSON.stringify(toolResult),
        });
      }

      // Feed tool results back
      messages.push({ role: 'user', content: toolResults });

    } else {
      // End of turn — extract text reply
      finalReply = content.find(b => b.type === 'text')?.text || 'Done.';
      break;
    }
  }

  // Update conversation history with final state (trim if needed)
  history.push({ role: 'assistant', content: finalReply });
  if (history.length > MAX_HISTORY * 2) history.splice(0, 2);

  return finalReply;
}

// ── Slash commands ────────────────────────────────────────────────────────────
function handleCommands(text, chatId) {
  const t = text.trim().toLowerCase();
  if (t === '/start') {
    return `Hey Ashley! Your AI OS is live.\n\nJust tell me your numbers in any way — "45 contacts, 2 appts set" — and I'll save them to the database.\n\nOr ask me anything about your business.\n\n/help for commands.`;
  }
  if (t === '/clear') return '__CLEAR__';
  if (t === '/help') {
    return `*ProAgent AI OS*\n\n*Logging numbers:* Just tell me — "45 contacts, 2 appts set, 1 met" — I'll save it.\n\n*Commands:*\n/clear — reset chat\n/help — this message\n\n*Live data:* Run /brief in Claude Code for pipeline + weekly progress.`;
  }
  return null;
}

// ── Fireflies webhook ─────────────────────────────────────────────────────────

async function getAgentConfig(agentId, env) {
  const rows = await sbGet(
    env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY,
    `agents?agent_id=eq.${encodeURIComponent(agentId)}&active=eq.true&limit=1`,
  );
  return rows[0] || null;
}

function buildTitleRegex(recruiterNames) {
  const pattern = recruiterNames
    .map(name => name.trim().split(/\s+/).map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+'))
    .join('|');
  return new RegExp(`^(.+?)\\s+(?:&|and)\\s+(${pattern})\\s*$`, 'i');
}

async function handleFireflies(request, env, agentId) {
  // Load agent config from Supabase
  const agent = await getAgentConfig(agentId, env);
  if (!agent) {
    console.warn(`Fireflies: unknown agent_id "${agentId}"`);
    return new Response(`Unknown agent: ${agentId}`, { status: 404 });
  }

  const AGENT_INTERNAL_EMAILS = new Set([
    ...(agent.my_emails || []),
    ...(agent.internal_emails || []),
  ].map(e => e.toLowerCase()));

  const RECRUITER_NAMES = agent.recruiter_names || ['Michelle Wilson', 'Chad Cooley'];
  const TITLE_RE = buildTitleRegex(RECRUITER_NAMES);
  const AGENT_GHL_KEY = agent.ghl_api_key;
  const AGENT_LOCATION = agent.ghl_location_id;
  const AGENT_CHAT_ID = agent.notification_telegram_chat_id;
  let payload;
  try {
    payload = await request.json();
  } catch {
    return new Response('Bad JSON', { status: 400 });
  }

  const title = payload.title || payload.meeting_name || '';
  const dateRaw = payload.date || payload.start_time || '';
  const meetingDate = dateRaw ? new Date(dateRaw).toISOString().slice(0, 10) : new Date().toISOString().slice(0, 10);

  // Only process qualifying recruiter events
  if (!TITLE_RE.test(title)) {
    console.log(`Fireflies [${agentId}]: skipping "${title}"`);
    return new Response('OK', { status: 200 });
  }

  // Build note content from Fireflies summary
  const summary = payload.summary || {};
  const overview = summary.overview || summary.short_summary || payload.short_summary || '';
  const actionItems = summary.action_items || payload.action_items || [];
  const keywords = summary.keywords || [];

  const actionLines = Array.isArray(actionItems) && actionItems.length
    ? actionItems.map(a => `☐ ${typeof a === 'string' ? a : a.text || JSON.stringify(a)}`).join('\n')
    : '(none)';

  const noteBody = [
    `=== Meeting Notes: ${meetingDate} ===`,
    '',
    overview,
    '',
    'ACTION ITEMS',
    actionLines,
    keywords.length ? `\nKey Topics: ${keywords.slice(0, 8).join(', ')}` : '',
    '',
    `Transcript: ${payload.transcript_url || payload.video_url || '(see Fireflies)'}`,
  ].filter(l => l !== null).join('\n').trim();

  // ── Find GHL contact (3 layers) ──────────────────────────────────────────

  let ghlContactId = null;
  let contactName = '';

  // Layer 3: Supabase mapping (most reliable — set by calendar_to_ghl.py)
  const mapRows = await sbGet(
    env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY,
    `meeting_contact_map?meeting_title=eq.${encodeURIComponent(title)}&select=ghl_contact_id,ghl_contact_name&limit=1`,
  );
  if (mapRows.length) {
    ghlContactId = mapRows[0].ghl_contact_id;
    contactName = mapRows[0].ghl_contact_name || '';
    console.log(`Fireflies [${agentId}]: found via mapping — ${contactName}`);
  }

  // Layer 1: Attendee email match
  if (!ghlContactId) {
    const attendees = payload.attendees || payload.participants || [];
    const prospectEmails = attendees
      .map(a => (typeof a === 'string' ? a : a.email || '').toLowerCase())
      .filter(e => e && !AGENT_INTERNAL_EMAILS.has(e));

    for (const email of prospectEmails) {
      const result = await ghlSearchByEmailForAgent(email, AGENT_GHL_KEY, AGENT_LOCATION);
      if (result) {
        ghlContactId = result.id;
        contactName = result.contactName || result.firstName || email;
        break;
      }
    }
  }

  // Layer 2: Title name search
  if (!ghlContactId) {
    const match = title.match(TITLE_RE);
    if (match) {
      const prospectName = match[1].trim();
      const result = await ghlSearchByNameForAgent(prospectName, AGENT_GHL_KEY, AGENT_LOCATION);
      if (result) {
        ghlContactId = result.id;
        contactName = result.contactName || result.firstName || prospectName;
      }
    }
  }

  // ── Post note to GHL ─────────────────────────────────────────────────────

  let ghlUpdated = false;
  if (ghlContactId) {
    try {
      await ghlAddNoteForAgent(ghlContactId, noteBody, AGENT_GHL_KEY);
      ghlUpdated = true;
    } catch (err) {
      console.error(`Fireflies [${agentId}]: GHL note failed — ${err.message}`);
    }
  }

  // ── Notify agent via Telegram ─────────────────────────────────────────────

  const statusLine = ghlUpdated
    ? `✅ GHL updated for *${contactName}*`
    : `⚠️ Could not find GHL contact for "${title}"`;

  const tgMsg = [
    `🎙 *Meeting Transcribed*`,
    `📅 ${meetingDate} | ${title}`,
    statusLine,
    '',
    overview ? `*Overview:*\n${overview.slice(0, 400)}${overview.length > 400 ? '...' : ''}` : '',
    actionItems.length ? `\n*Action Items:*\n${actionLines}` : '',
  ].filter(Boolean).join('\n');

  if (AGENT_CHAT_ID) {
    await sendMessage(env.TELEGRAM_BOT_TOKEN, AGENT_CHAT_ID, tgMsg);
  }

  return new Response('OK', { status: 200 });
}

// ── GHL helpers (per-agent credentials) ──────────────────────────────────────

async function ghlSearchByEmailForAgent(email, apiKey, locationId) {
  const resp = await fetch(
    `https://rest.gohighlevel.com/v1/contacts/?query=${encodeURIComponent(email)}&locationId=${locationId}`,
    { headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' } },
  );
  if (!resp.ok) return null;
  const data = await resp.json();
  return (data.contacts || []).find(c => (c.email || '').toLowerCase() === email.toLowerCase()) || null;
}

async function ghlSearchByNameForAgent(name, apiKey, locationId) {
  const resp = await fetch(
    `https://rest.gohighlevel.com/v1/contacts/?query=${encodeURIComponent(name)}&locationId=${locationId}`,
    { headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' } },
  );
  if (!resp.ok) return null;
  const data = await resp.json();
  return (data.contacts || [])[0] || null;
}

async function ghlAddNoteForAgent(contactId, body, apiKey) {
  const resp = await fetch(
    `https://rest.gohighlevel.com/v1/contacts/${contactId}/notes/`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    },
  );
  if (!resp.ok) throw new Error(`GHL ${resp.status}: ${await resp.text()}`);
}

// ── Pending note approvals (inbound lead replies) ─────────────────────────────

async function answerCallbackQuery(botToken, callbackQueryId, text) {
  await fetch(`https://api.telegram.org/bot${botToken}/answerCallbackQuery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ callback_query_id: callbackQueryId, text, show_alert: false }),
  });
}

async function editMessageReplyMarkup(botToken, chatId, messageId, replyMarkup) {
  await fetch(`https://api.telegram.org/bot${botToken}/editMessageReplyMarkup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, message_id: messageId, reply_markup: replyMarkup }),
  });
}

async function ghlAddNote(contactId, noteBody, ghlApiKey) {
  const resp = await fetch(
    `https://rest.gohighlevel.com/v1/contacts/${contactId}/notes/`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${ghlApiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ body: noteBody }),
    },
  );
  if (!resp.ok) throw new Error(`GHL ${resp.status}: ${await resp.text()}`);
}

async function handleNoteCallback(env, callbackQuery) {
  const data     = callbackQuery.data || '';
  const chatId   = callbackQuery.message?.chat?.id;
  const msgId    = callbackQuery.message?.message_id;
  const queryId  = callbackQuery.id;

  if (!ALLOWED_CHAT_IDS.has(chatId)) return;

  const [action, pendingId] = data.split(':');
  if (!pendingId) return;

  // Fetch the pending note from Supabase
  const rows = await sbGet(
    env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY,
    `pending_notes?id=eq.${pendingId}&status=eq.pending&limit=1`,
  );

  if (!rows.length) {
    await answerCallbackQuery(env.TELEGRAM_BOT_TOKEN, queryId, 'Already actioned or not found.');
    return;
  }

  const note = rows[0];

  if (action === 'approve_note') {
    try {
      await ghlAddNote(note.contact_id, note.note_body, env.GHL_PROAGENT_API_KEY);
      await sbPatch(
        env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY,
        `pending_notes?id=eq.${pendingId}`,
        { status: 'approved', resolved_at: new Date().toISOString() },
      );
      await answerCallbackQuery(env.TELEGRAM_BOT_TOKEN, queryId, '✅ Note added to GHL!');
      // Remove the inline keyboard to prevent double-taps
      await editMessageReplyMarkup(env.TELEGRAM_BOT_TOKEN, chatId, msgId, JSON.stringify({ inline_keyboard: [] }));
      await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, `✅ Note added to *${note.contact_name}*'s GHL record.`);
    } catch (err) {
      await answerCallbackQuery(env.TELEGRAM_BOT_TOKEN, queryId, '❌ GHL update failed — try again.');
      console.error('approve_note error:', err);
    }
  } else if (action === 'skip_note') {
    await sbPatch(
      env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY,
      `pending_notes?id=eq.${pendingId}`,
      { status: 'skipped', resolved_at: new Date().toISOString() },
    );
    await answerCallbackQuery(env.TELEGRAM_BOT_TOKEN, queryId, 'Skipped.');
    await editMessageReplyMarkup(env.TELEGRAM_BOT_TOKEN, chatId, msgId, JSON.stringify({ inline_keyboard: [] }));
  }
}

// ── Main handler ──────────────────────────────────────────────────────────────
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Fireflies webhook route — /fireflies/{agent_id}
    if (request.method === 'POST' && url.pathname.startsWith('/fireflies/')) {
      const agentId = url.pathname.split('/')[2];
      if (!agentId) return new Response('Missing agent_id', { status: 400 });
      return handleFireflies(request, env, agentId);
    }

    if (request.method !== 'POST') {
      return new Response('ProAgent AI OS is running.', { status: 200 });
    }

    let update;
    try { update = await request.json(); }
    catch { return new Response('Bad request', { status: 400 }); }

    // Handle inline keyboard button taps (approve/skip note)
    if (update?.callback_query) {
      await handleNoteCallback(env, update.callback_query);
      return new Response('OK', { status: 200 });
    }

    const message = update?.message;
    if (!message?.text) return new Response('OK', { status: 200 });

    const chatId = message.chat.id;
    const text = message.text;

    if (!ALLOWED_CHAT_IDS.has(chatId)) {
      return new Response('OK', { status: 200 });
    }

    try {
      const cmd = handleCommands(text, chatId);
      if (cmd === '__CLEAR__') {
        conversations.delete(chatId);
        await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, 'Cleared! Fresh start.');
      } else if (cmd) {
        await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, cmd);
      } else {
        // Check decision commands before sending to Claude
        const decisionReply = await handleDecisionCommands(
          env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, text
        );
        if (decisionReply) {
          await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, decisionReply);
        } else {
          const reply = await callClaude(
            env.ANTHROPIC_API_KEY,
            env.SUPABASE_URL,
            env.SUPABASE_SERVICE_ROLE_KEY,
            chatId,
            text,
          );
          await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, reply);
        }
      }
    } catch (err) {
      console.error(err);
      await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, 'Something went wrong. Try again.');
    }

    return new Response('OK', { status: 200 });
  },
};
