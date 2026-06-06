-- Multi-agent config table
-- Each row = one agent using the attraction system.
-- Written by setup.py, read by the Cloudflare Worker to route Fireflies webhooks.
CREATE TABLE IF NOT EXISTS agents (
  agent_id                      TEXT PRIMARY KEY,
  agent_name                    TEXT NOT NULL,
  recruiter_names               TEXT[]  DEFAULT ARRAY['Michelle Wilson', 'Chad Cooley'],
  my_emails                     TEXT[]  DEFAULT '{}',
  internal_emails               TEXT[]  DEFAULT '{}',
  ghl_api_key                   TEXT NOT NULL,
  ghl_location_id               TEXT NOT NULL,
  ghl_tags                      TEXT[]  DEFAULT ARRAY['agent', 'agentnewsletter'],
  notification_telegram_chat_id BIGINT,
  notification_email            TEXT,
  reengage_threshold_days       INTEGER DEFAULT 60,
  active                        BOOLEAN DEFAULT TRUE,
  created_at                    TIMESTAMPTZ DEFAULT NOW()
);
