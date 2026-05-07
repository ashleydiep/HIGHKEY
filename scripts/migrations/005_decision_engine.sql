-- Decision Engine: fresh install
-- Run via: scripts/decisions/apply_migration.py

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question TEXT NOT NULL,
  context TEXT,
  options JSONB DEFAULT '[]',
  chosen TEXT,
  rationale TEXT,
  expected_outcome TEXT,
  actual_outcome TEXT,
  outcome_assessed_at TIMESTAMPTZ,
  tags JSONB DEFAULT '[]',
  company TEXT,
  confidence_score NUMERIC,
  pattern_id UUID,
  embedding vector(1024),
  source TEXT NOT NULL DEFAULT 'manual',
  status TEXT NOT NULL DEFAULT 'logged',
  module TEXT,
  reason_category TEXT,
  rejection_note TEXT,
  re_surface_at TIMESTAMPTZ,
  issue_signature TEXT,
  short_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decisions_company ON decisions(company);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_outcome_due ON decisions(outcome_assessed_at)
  WHERE actual_outcome IS NULL;
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status)
  WHERE status IN ('pending', 'rejected');
CREATE INDEX IF NOT EXISTS idx_decisions_source ON decisions(source);
CREATE INDEX IF NOT EXISTS idx_decisions_pending ON decisions(created_at)
  WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_decisions_re_surface ON decisions(re_surface_at)
  WHERE re_surface_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_decisions_issue_signature ON decisions(issue_signature)
  WHERE issue_signature IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_decisions_short_id ON decisions(short_id)
  WHERE short_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_decisions_embedding ON decisions
  USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS decision_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_name TEXT NOT NULL UNIQUE,
  description TEXT,
  similar_decisions JSONB DEFAULT '[]',
  success_rate NUMERIC,
  total_decisions INTEGER DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION semantic_search(
  query_embedding vector(1024),
  match_threshold float DEFAULT 0.3,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  source_type text,
  source_id text,
  title text,
  content text,
  company text,
  similarity float,
  created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
    SELECT
      'decision'::text as source_type,
      d.id::text as source_id,
      d.question as title,
      COALESCE(d.chosen, '') || ' — ' || COALESCE(d.rationale, '') as content,
      d.company,
      1 - (d.embedding <=> query_embedding) as similarity,
      d.created_at
    FROM decisions d
    WHERE d.embedding IS NOT NULL
      AND 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

COMMIT;
