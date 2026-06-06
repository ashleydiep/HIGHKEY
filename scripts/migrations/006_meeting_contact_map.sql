-- Meeting → GHL contact mapping
-- Written by calendar_to_ghl.py when it creates or finds a contact.
-- Read by the Cloudflare Worker when a Fireflies webhook arrives.
CREATE TABLE IF NOT EXISTS meeting_contact_map (
  id              SERIAL PRIMARY KEY,
  meeting_title   TEXT NOT NULL,          -- e.g. "Shana Hoople & Michelle Wilson"
  ghl_contact_id  TEXT NOT NULL,          -- GHL contact source_id
  ghl_contact_name TEXT,                  -- for debugging
  event_date      TEXT,                   -- YYYY-MM-DD
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(meeting_title)                   -- upsert by title
);
