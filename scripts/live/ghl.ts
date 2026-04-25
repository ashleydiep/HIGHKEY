// Live GHL queries — ever-changing pipeline state.
// Claude calls these functions at question time (not synced to Supabase).
// Usage: import and call directly from Claude Code sessions or analysis scripts.

const GHL_KEY = process.env.GHL_PROAGENT_API_KEY;
const BASE = 'https://rest.gohighlevel.com/v1';

const PIPELINES = {
  agent: 'okPDhRpZFpOyibTiHDcU',
  marketing: 'v1cUpUAhxumYVkXuhK22',
  realEstate: '601one8uXUxoi9Hh315z',
};

async function ghlGet(path: string) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${GHL_KEY}`, 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`GHL ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function getLivePipeline(pipeline: 'agent' | 'marketing' | 'realEstate') {
  const pipelineId = PIPELINES[pipeline];
  const [pipelineData, oppsData] = await Promise.all([
    ghlGet('/pipelines/'),
    ghlGet(`/pipelines/${pipelineId}/opportunities/?limit=100`),
  ]);

  const pipelineMeta = pipelineData.pipelines?.find((p: any) => p.id === pipelineId);
  const stageMap: Record<string, string> = {};
  for (const stage of pipelineMeta?.stages ?? []) stageMap[stage.id] = stage.name;

  const byStage: Record<string, any[]> = {};
  for (const opp of oppsData.opportunities ?? []) {
    const stageName = stageMap[opp.pipelineStageId] ?? 'Unknown';
    if (!byStage[stageName]) byStage[stageName] = [];
    byStage[stageName].push({
      id: opp.id,
      name: opp.name,
      contact: opp.contact?.name,
      status: opp.status,
      value: opp.monetaryValue,
      updatedAt: opp.updatedAt,
    });
  }

  return {
    pipeline: pipelineMeta?.name,
    totalOpportunities: oppsData.meta?.total ?? oppsData.opportunities?.length,
    byStage,
  };
}

export async function getContact(contactId: string) {
  return ghlGet(`/contacts/${contactId}`);
}

export async function searchContacts(query: string) {
  return ghlGet(`/contacts/?query=${encodeURIComponent(query)}&limit=20`);
}

export async function getRecentActivity(limit = 20) {
  const data = await ghlGet(`/contacts/?limit=${limit}&sortBy=date_updated&sortOrder=desc`);
  return data.contacts?.map((c: any) => ({
    id: c.id,
    name: c.contactName,
    tags: c.tags,
    lastActivity: c.lastActivity,
    dateUpdated: c.dateUpdated,
  }));
}
