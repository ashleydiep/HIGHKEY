/**
 * ProAgent AI OS — Telegram Bot (Cloudflare Worker)
 * Receives Telegram messages → calls Claude with tool use → replies
 * Tools: save_daily_kpis (writes to Supabase)
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

const conversations = new Map();
const MAX_HISTORY = 10;

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

// ── Main handler ──────────────────────────────────────────────────────────────
export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('ProAgent Telegram Bot is running.', { status: 200 });
    }

    let update;
    try { update = await request.json(); }
    catch { return new Response('Bad request', { status: 400 }); }

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
        const reply = await callClaude(
          env.ANTHROPIC_API_KEY,
          env.SUPABASE_URL,
          env.SUPABASE_SERVICE_ROLE_KEY,
          chatId,
          text,
        );
        await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, reply);
      }
    } catch (err) {
      console.error(err);
      await sendMessage(env.TELEGRAM_BOT_TOKEN, chatId, 'Something went wrong. Try again.');
    }

    return new Response('OK', { status: 200 });
  },
};
