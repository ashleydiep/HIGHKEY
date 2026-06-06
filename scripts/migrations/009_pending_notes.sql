-- Pending GHL note approvals
-- Created by the inbound flow in lead_followup.py
-- Telegram bot reads this table to handle approve_note / skip_note callbacks

CREATE TABLE IF NOT EXISTS pending_notes (
    id               uuid PRIMARY KEY,
    contact_id       text NOT NULL,
    contact_name     text,
    note_body        text NOT NULL,
    reply_text       text,
    interest_level   text,          -- hot | warm | cold
    next_step        text,
    status           text NOT NULL DEFAULT 'pending',  -- pending | approved | skipped
    created_at       timestamptz NOT NULL DEFAULT now(),
    resolved_at      timestamptz
);

-- Speed up Telegram bot lookups by id
CREATE INDEX IF NOT EXISTS pending_notes_id_status ON pending_notes (id, status);

-- Auto-expire old pending notes after 7 days (cleanup)
CREATE INDEX IF NOT EXISTS pending_notes_created_at ON pending_notes (created_at);
