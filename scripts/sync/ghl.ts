import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import { supabase } from '../utils/db.ts';
import { embedBatch, chunkArray } from '../utils/voyage.ts';

const GHL_KEY = process.env.GHL_PROAGENT_API_KEY;
const LOCATION_ID = process.env.GHL_PROAGENT_LOCATION_ID;
if (!GHL_KEY || !LOCATION_ID) throw new Error('Missing GHL_PROAGENT_API_KEY or GHL_PROAGENT_LOCATION_ID');

const BASE = 'https://rest.gohighlevel.com/v1';
const STATE_FILE = join(process.cwd(), 'data/sync-state/ghl.json');

const PIPELINE_NAMES: Record<string, string> = {
  okPDhRpZFpOyibTiHDcU: 'Agent Pipeline',
  v1cUpUAhxumYVkXuhK22: 'Marketing Pipeline',
  '601one8uXUxoi9Hh315z': 'Real Estate Pipeline',
};

// Stage name lookup built at runtime from pipeline fetch
const stageNames: Record<string, string> = {};

// ─── state ───────────────────────────────────────────────────────────────────

function loadState(): { lastContactSync: string | null; lastOppSync: string | null; lastNoteSync: string | null } {
  if (existsSync(STATE_FILE)) return JSON.parse(readFileSync(STATE_FILE, 'utf8'));
  return { lastContactSync: null, lastOppSync: null, lastNoteSync: null };
}

function saveState(state: ReturnType<typeof loadState>) {
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

// ─── GHL API helpers ──────────────────────────────────────────────────────────

async function ghlGet(path: string) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${GHL_KEY}`, 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`GHL API error ${res.status} for ${path}: ${await res.text()}`);
  return res.json();
}

// ─── contacts ────────────────────────────────────────────────────────────────

async function syncContacts(since: string | null) {
  console.log('[contacts] starting sync...');
  let total = 0;
  let nextPageUrl: string | null = null;
  let page = 1;

  do {
    let url = nextPageUrl
      ? nextPageUrl.replace('http://', 'https://')
      : `${BASE}/contacts/?limit=100${since ? `&startAfter=${new Date(since).getTime()}` : ''}`;

    const data = await ghlGet(url.replace(BASE, ''));
    const contacts = data.contacts ?? [];
    if (contacts.length === 0) break;

    const rows = contacts.map((c: any) => ({
      source_id: c.id,
      location_id: c.locationId ?? LOCATION_ID,
      first_name: c.firstName ?? null,
      last_name: c.lastName ?? null,
      full_name: c.contactName ?? null,
      email: c.email ?? null,
      phone: c.phone ?? null,
      contact_type: c.type ?? null,
      tags: c.tags ?? [],
      source: c.source ?? null,
      city: c.city ?? null,
      state: c.state ?? null,
      country: c.country ?? null,
      assigned_to: c.assignedTo ?? null,
      dnd: c.dnd ?? false,
      date_added: c.dateAdded ?? null,
      date_updated: c.dateUpdated ?? null,
      metadata: { customFields: c.customField ?? [] },
      _synced_at: new Date().toISOString(),
    }));

    const { error } = await supabase
      .from('ghl_contacts')
      .upsert(rows, { onConflict: 'source_id' });

    if (error) throw new Error(`Contacts upsert error: ${error.message}`);
    total += rows.length;
    console.log(`[contacts] page ${page}: ${rows.length} upserted (${total} total)`);

    nextPageUrl = data.meta?.nextPageUrl ?? null;
    page++;
  } while (nextPageUrl);

  console.log(`[contacts] done — ${total} contacts synced`);
  return total;
}

// ─── opportunities ────────────────────────────────────────────────────────────

async function loadStageNames() {
  const data = await ghlGet('/pipelines/');
  for (const pipeline of data.pipelines ?? []) {
    for (const stage of pipeline.stages ?? []) {
      stageNames[stage.id] = stage.name;
    }
  }
}

async function syncOpportunities() {
  console.log('[opportunities] starting sync...');
  await loadStageNames();
  let total = 0;

  for (const [pipelineId, pipelineName] of Object.entries(PIPELINE_NAMES)) {
    let nextPageUrl: string | null = null;
    let page = 1;

    do {
      let path = nextPageUrl
        ? nextPageUrl.replace('http://', 'https://').replace(BASE, '')
        : `/pipelines/${pipelineId}/opportunities/?limit=100`;

      const data = await ghlGet(path);
      const opps = data.opportunities ?? [];
      if (opps.length === 0) break;

      const rows = opps.map((o: any) => ({
        source_id: o.id,
        name: o.name ?? null,
        pipeline_id: pipelineId,
        pipeline_name: pipelineName,
        stage_id: o.pipelineStageId ?? null,
        stage_name: stageNames[o.pipelineStageId] ?? null,
        status: o.status ?? null,
        monetary_value: o.monetaryValue ?? 0,
        contact_id: o.contact?.id ?? null,
        contact_name: o.contact?.name ?? null,
        contact_email: o.contact?.email ?? null,
        contact_phone: o.contact?.phone ?? null,
        contact_tags: o.contact?.tags ?? [],
        last_stage_change_at: o.lastStatusChangeAt ?? null,
        created_at: o.createdAt ?? null,
        _synced_at: new Date().toISOString(),
      }));

      const { error } = await supabase
        .from('ghl_opportunities')
        .upsert(rows, { onConflict: 'source_id' });

      if (error) throw new Error(`Opportunities upsert error: ${error.message}`);
      total += rows.length;
      console.log(`[opportunities] ${pipelineName} page ${page}: ${rows.length} upserted`);

      nextPageUrl = data.meta?.nextPageUrl ?? null;
      page++;
    } while (nextPageUrl);
  }

  console.log(`[opportunities] done — ${total} opportunities synced`);
  return total;
}

// ─── notes ────────────────────────────────────────────────────────────────────

async function syncNotes(since: string | null) {
  console.log('[notes] fetching contact list for note scan...');

  // Collect all contact IDs (pull fresh for incremental note sync)
  const allContactIds: { id: string; name: string }[] = [];
  let nextPageUrl: string | null = null;

  do {
    let path = nextPageUrl
      ? nextPageUrl.replace('http://', 'https://').replace(BASE, '')
      : `/contacts/?limit=100`;

    const data = await ghlGet(path);
    for (const c of data.contacts ?? []) {
      // For incremental runs, only check contacts updated since last sync
      if (since) {
        const updatedAt = new Date(c.dateUpdated ?? 0).getTime();
        const sinceMs = new Date(since).getTime();
        if (updatedAt < sinceMs) continue;
      }
      allContactIds.push({ id: c.id, name: c.contactName ?? '' });
    }
    nextPageUrl = data.meta?.nextPageUrl ?? null;
  } while (nextPageUrl);

  console.log(`[notes] checking ${allContactIds.length} contacts for notes`);

  let totalNotes = 0;
  const allNotes: { source_id: string; contact_id: string; contact_name: string; body: string; date_added: string | null }[] = [];

  for (const contact of allContactIds) {
    try {
      const data = await ghlGet(`/contacts/${contact.id}/notes/`);
      for (const note of data.notes ?? []) {
        if (!note.body?.trim()) continue;
        allNotes.push({
          source_id: note.id,
          contact_id: contact.id,
          contact_name: contact.name,
          body: note.body,
          date_added: note.dateAdded ?? null,
        });
      }
    } catch {
      // Skip contacts with note fetch errors
    }
  }

  if (allNotes.length === 0) {
    console.log('[notes] no notes found');
    return 0;
  }

  console.log(`[notes] embedding ${allNotes.length} notes in batches...`);

  for (const batch of chunkArray(allNotes, 50)) {
    const embeddings = await embedBatch(batch.map((n) => n.body));

    const rows = batch.map((note, i) => ({
      source_id: note.source_id,
      contact_id: note.contact_id,
      contact_name: note.contact_name,
      body: note.body,
      metadata: {},
      embedding: embeddings[i],
      embedding_model: 'voyage-3-large',
      date_added: note.date_added,
      _synced_at: new Date().toISOString(),
    }));

    const { error } = await supabase
      .from('ghl_notes')
      .upsert(rows, { onConflict: 'source_id' });

    if (error) throw new Error(`Notes upsert error: ${error.message}`);
    totalNotes += rows.length;
    console.log(`[notes] ${totalNotes}/${allNotes.length} notes embedded and stored`);
  }

  console.log(`[notes] done — ${totalNotes} notes synced`);
  return totalNotes;
}

// ─── main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log('=== GHL sync starting ===');
  const state = loadState();
  const now = new Date().toISOString();

  try {
    await syncContacts(state.lastContactSync);
    state.lastContactSync = now;
    saveState(state);

    await syncOpportunities();
    state.lastOppSync = now;
    saveState(state);

    await syncNotes(state.lastNoteSync);
    state.lastNoteSync = now;
    saveState(state);

    console.log('=== GHL sync complete ===');
  } catch (err) {
    console.error('GHL sync failed:', err);
    process.exit(1);
  }
}

main();
