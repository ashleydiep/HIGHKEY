-- Add agent recruitment funnel columns to daily_kpis
-- Run in Supabase: Dashboard → SQL Editor → paste → Run

ALTER TABLE daily_kpis
  ADD COLUMN IF NOT EXISTS agent_contacts          INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS agent_discoveries_set   INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS agent_discoveries_met   INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS agent_3ways_set         INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS agent_3ways_met         INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS agent_verbals           INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS agent_onboarded         INT NOT NULL DEFAULT 0;
